"""Synthetic public metadata/audio and real SQLite/JWT boundaries only."""
import json
import threading
import time
from types import SimpleNamespace

import pytest


def test_artwork_sources_and_limits(monkeypatch):
    from swingmusic import spotify_import as s
    import io
    from PIL import Image
    cover='https://i.scdn.co/image/'+'a'*40
    track='https://image-cdn-fa.spotifycdn.com/image/'+'b'*40
    assert s.artwork_url({'coverArt':{'sources':[{'url':cover}]}})==cover
    assert s.artwork_url({'visualIdentity':{'image':[{'url':track,'maxHeight':640}]}})==track
    assert s.artwork_url({'visualIdentity':None,'coverArt':[]}) is None
    for bad in ['http://i.scdn.co/image/'+'a'*40,'https://user@i.scdn.co/image/'+'a'*40,
                'https://i.scdn.co.evil.test/image/'+'a'*40,'https://127.0.0.1/image/'+'a'*40,
                'https://i.scdn.co:443/image/'+'a'*40,'https://[bad','file:///image/'+'a'*40]:
        assert not s.valid_artwork_url(bad)
    assert s.valid_artwork_url('https://mosaic.scdn.co/640/'+'a'*160)
    raw=io.BytesIO();Image.new('RGB',(900,600),'#318e5f').save(raw,'PNG')
    monkeypatch.setattr(s,'public_bytes',lambda url,limit:raw.getvalue())
    with s.artwork_image(track) as image:assert image.size==(800,533)
    monkeypatch.setattr(s,'public_bytes',lambda *_:b'<html>Not artwork</html>')
    with pytest.raises(s.ImportProblem,match='could not be read'):s.artwork_image(track)


def test_download_embeds_visual_identity_artwork(tmp_path,monkeypatch):
    from swingmusic import spotify_import as s
    from PIL import Image
    from mutagen.mp3 import MP3
    import io,subprocess,imageio_ffmpeg
    raw=io.BytesIO();Image.new('RGB',(400,400),'#54389e').save(raw,'PNG')
    entity={'releaseDate':{'isoString':'2026-10-01T00:00:00Z'},'visualIdentity':{'image':[{'url':'https://image-cdn-fa.spotifycdn.com/image/'+'a'*40,'maxHeight':400}]}}
    page='<script id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'state':{'data':{'entity':entity}}}}})+'</script>'
    monkeypatch.setattr(s,'public_bytes',lambda url,*_:page.encode() if '/embed/' in url else raw.getvalue())
    monkeypatch.setattr(s,'tool_path',lambda *_:'synthetic-tool')
    def run(args,*_):
        if args[-1].startswith('ytsearch'):
            return json.dumps({'entries':[{'id':'abcdefghijk','title':'Fixture Song','uploader':'Fixture Artist - Topic','duration':2}]})
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-f','lavfi','-i','sine=frequency=440:duration=2','-q:a','5',str(tmp_path/'audio.mp3')],check=True)
        return ''
    monkeypatch.setattr(s,'run_tool',run)
    file=s.download_audio({'id':'a'*22,'title':'Fixture Song','artist':'Fixture Artist','duration':2},tmp_path,threading.Event())
    tags=MP3(file).tags
    assert len(tags.getall('APIC'))==1 and str(tags['TDRC'])=='2026'
    with Image.open(io.BytesIO(tags.getall('APIC')[0].data)) as image:assert image.format=='JPEG' and image.size==(400,400)


def test_rare_song_search_and_failure_messages(monkeypatch):
    from swingmusic import spotify_import as s
    track={'title':'My Only Only','artist':'Fortune The Voice','duration':173}
    exact={'id':'0TapMXMuuGI','title':'My Only Only','uploader':'Fortune The Voice - Topic','duration':173}
    unrelated={'id':'2Ef7JtTqXOE','title':'Jimmy Fortune sings My Only Love','uploader':'Country Road TV','duration':231}
    calls=[]
    def search(args,*_):
        calls.append(args[-1])
        return json.dumps({'entries':[exact] if '"My Only Only"' in args[-1] else [unrelated]})
    monkeypatch.setattr(s,'run_tool',search)
    stop=threading.Event()
    assert s.search_audio(track,['tool'],stop)==exact
    assert calls==['ytsearch5:"My Only Only" "Fortune The Voice"']
    # Distributor suffixes also work for short names and short song titles.
    assert s.choose_match({'title':'Hello','artist':'Adele','duration':295},[
        {'id':'abcdefghijk','title':'Hello (Official Audio)','uploader':'Adele - Topic','duration':295}
    ])['id']=='abcdefghijk'
    assert s.choose_match({'title':'Baby','artist':'Justin Bieber, Ludacris','duration':214},[
        {'id':'abcdefghijk','title':'Justin Bieber - Baby ft. Ludacris (Official Music Video)','uploader':'JustinBieberVEVO','duration':214}
    ])['id']=='abcdefghijk'
    assert s.choose_match({'title':'APT.','artist':'ROSÉ, Bruno Mars','duration':170},[
        {'id':'abcdefghijk','title':'ROSÉ & Bruno Mars - APT. (Official MV)','uploader':'ROSÉ','duration':170}
    ])['id']=='abcdefghijk'
    # Fallback runs only when the first query cannot yield a confident match.
    replies=iter([json.dumps({'entries':[unrelated]}),json.dumps({'entries':[exact]})])
    monkeypatch.setattr(s,'run_tool',lambda *_:next(replies))
    assert s.search_audio(track,['tool'],stop)==exact
    for response,message in [(json.dumps({'entries':[unrelated]}),'right title, artist and duration'),
                              ('<html>upstream error</html>','unreadable response'),
                              ('{"entries":{}}','unreadable response')]:
        monkeypatch.setattr(s,'run_tool',lambda *_,value=response:value)
        with pytest.raises(s.ImportProblem,match=message):s.search_audio(track,['tool'],stop)
    for change in ({'duration':300},{'title':'My Only Only (Karaoke)'},{'uploader':'Another Artist'}):
        with pytest.raises(s.ImportProblem):s.choose_match(track,[{**exact,**change}])
    stop.set()
    with pytest.raises(s.ImportCancelled):s.search_audio(track,['tool'],stop)


def test_metadata_and_matching_boundaries(monkeypatch):
    from swingmusic import spotify_import as s
    valid="https://open.spotify.com/playlist/"+"a"*22
    assert s.playlist_url(valid+"?si=ignored")==valid
    assert s.playlist_url("spotify:playlist:"+"a"*22)==valid
    for value in ("http://open.spotify.com/playlist/"+"a"*22,"https://open.spotify.com.evil.test/playlist/"+"a"*22,"https://user@open.spotify.com/playlist/"+"a"*22,"https://127.0.0.1/private","file:///C:/private",valid+"/extra",None):
        with pytest.raises(s.ImportProblem):s.playlist_url(value)
    entity={"title":"Synthetic <playlist>","trackList":[{"uri":"spotify:track:"+"b"*22,"title":"Synthetic Song","subtitle":"Test Artist","duration":60000},{"uri":"spotify:episode:"+"c"*22,"title":"Not a song"}]}
    page='<script type="application/json" id="__NEXT_DATA__">'+json.dumps({"props":{"pageProps":{"state":{"data":{"entity":entity}}}}})+'</script>'
    monkeypatch.setattr(s,"public_bytes",lambda *a,**k:page.encode())
    result=s.resolve_playlist(valid)
    assert len(result["tracks"])==1 and result["tracks"][0]["duration"]==60
    assert "may omit" in result["notice"]
    track=result["tracks"][0]
    assert s.normal('नमस्ते') and s.similarity('नमस्ते','संगीत')<.94
    assert s.similarity('!!!','???')==0
    wrong={"id":"abcdefghijk","title":"Synthetic Song karaoke","uploader":"Test Artist","duration":60}
    good={**wrong,"title":"Test Artist - Synthetic Song (Official Audio)"}
    assert s.choose_match(track,[wrong,good])==good
    for candidate in (wrong,{**good,"duration":200},{**good,"id":"http://evil"},{**good,"uploader":"Elsewhere","title":"Unrelated song"}):
        with pytest.raises(s.ImportProblem):s.choose_match(track,[candidate])


def test_import_jobs_and_security(tmp_path,monkeypatch):
    from flask import Flask
    from flask_jwt_extended import JWTManager,create_access_token
    from swingmusic.settings import Paths,Singleton
    from swingmusic.db.engine import DbEngine
    monkeypatch.setattr(Singleton,'_instances',{})
    monkeypatch.setattr(DbEngine,'_engine',None)
    Paths(config_parent=tmp_path/'private',client_dir=tmp_path/'client')
    from swingmusic.setup import run_setup
    run_setup()
    from swingmusic.db.userdata import UserTable,PlaylistTable
    from swingmusic.store.tracks import TrackStore
    from swingmusic.listening import install,principal
    from swingmusic import spotify_import as s
    users=[]
    for name in ('Owner','Other'):
        UserTable.insert_one({'username':name,'password':'synthetic','roles':['user'],'extra':{}})
        users.append(UserTable.get_by_username(name))
    item=SimpleNamespace(trackhash='f'*16,title='Existing Song',artists=[{'name':'Test Artist'}],duration=60,image='test.webp',album='Fixture',albumhash='e'*16,color='#123456',date=2026,explicit=False,last_mod=1)
    TrackStore.trackhashmap={item.trackhash:SimpleNamespace(get_best=lambda:item)}
    snapshot={'name':'Fixture playlist','source':'https://open.spotify.com/playlist/'+'a'*22,'notice':'Synthetic metadata', 'tracks':[{'id':'b'*22,'title':'Existing Song','artist':'Test Artist','duration':60,'hash':None,'status':'pending','message':''},{'id':'c'*22,'title':'Missing Song','artist':'Test Artist','duration':60,'hash':None,'status':'pending','message':''}]}
    import io
    from PIL import Image
    cover=io.BytesIO();Image.new('RGB',(400,400),'#167953').save(cover,'PNG')
    snapshot['artwork']='https://i.scdn.co/image/'+'a'*40
    monkeypatch.setattr(s,'public_bytes',lambda *_:cover.getvalue())
    import copy
    monkeypatch.setattr(s,'resolve_playlist',lambda value:copy.deepcopy(snapshot))
    app=Flask(__name__);app.config.update(JWT_SECRET_KEY='synthetic-test-signing-key-only-32-chars',JWT_VERIFY_SUB=False)
    jwt=JWTManager(app)
    @jwt.user_lookup_loader
    def lookup(_header,data):
        user=UserTable.get_by_id(data['sub']['id'])
        return user.todict() if user else None
    install(app)
    clients=[app.test_client(),app.test_client()];headers=[]
    for client,user in zip(clients,users):
        user=UserTable.get_by_id(user.id)
        with app.app_context():token=create_access_token(identity=user.todict())
        head={'Authorization':'Bearer '+token,'Origin':'http://localhost'}
        head['X-Music-CSRF']=client.get('/studio/bootstrap',headers=head).get_json()['csrf'];headers.append(head)
    owner,other=clients;h=headers[0];service=app.extensions['spotify_imports']
    assert app.test_client().get('/studio/imports').status_code==401
    assert owner.post('/studio/imports/preview',headers={**h,'Origin':'https://evil.test'},json={'url':'test'}).status_code==403
    assert owner.post('/studio/imports/preview',headers={k:v for k,v in h.items() if k!='X-Music-CSRF'},json={'url':'test'}).status_code==403
    job=owner.post('/studio/imports/preview',headers=h,json={'url':'test'}).get_json();jid=job['id']
    assert job['available']==1 and 'owner' not in job and 'user' not in job
    assert other.get('/studio/imports/'+jid,headers=headers[1]).status_code==404
    assert other.post('/studio/imports/'+jid+'/start',headers=headers[1],json={'download':False}).status_code==404
    assert other.get('/studio/imports',headers=headers[1]).get_json()['jobs']==[]
    gate=threading.Event();entered=threading.Event();original=service.work
    def delayed(*args):entered.set();gate.wait(5);original(*args)
    monkeypatch.setattr(service,'work',delayed)
    first=owner.post('/studio/imports/'+jid+'/start',headers=h,json={'download':False});assert first.status_code==202
    assert entered.wait(2)
    repeat=owner.post('/studio/imports/'+jid+'/start',headers=h,json={'download':False}).get_json()
    assert repeat['playlist']==first.get_json()['playlist'] and PlaylistTable.count()==1
    gate.set()
    def finished():
        for _ in range(200):
            value=owner.get('/studio/imports/'+jid,headers=h).get_json()
            if value['status'] not in s.ACTIVE:return value
            time.sleep(.025)
        pytest.fail('worker did not finish')
    done=finished();assert done['status']=='partial' and done['available']==1
    from swingmusic.db.engine import DbEngine
    with DbEngine.manager() as db:
        row=db.execute(__import__('sqlalchemy').select(PlaylistTable)).scalar()
    assert row.userid==users[0].id and row.trackhashes==[item.trackhash]
    assert row.image and (Paths().playlist_img_path/row.image).is_file()
    assert (Paths().playlist_img_path/('thumb_'+row.image)).is_file()
    assert other.post('/studio/imports/'+jid+'/artwork',headers=headers[1],json={}).status_code==404
    assert owner.post('/studio/imports/'+jid+'/artwork',headers={k:v for k,v in h.items() if k!='X-Music-CSRF'},json={}).status_code==403
    # Repair a legacy job without re-downloading audio or replacing its playlist.
    stored=service.load(jid,principal(UserTable.get_by_id(users[0].id)));stored.pop('artwork',None);service.save(stored)
    with DbEngine.manager(commit=True) as db:
        db.execute(__import__('sqlalchemy').update(PlaylistTable).where(PlaylistTable.id==row.id).values(image=None))
    entity={'coverArt':{'sources':[{'url':'https://i.scdn.co/image/'+'a'*40}]}}
    page='<script id="__NEXT_DATA__">'+json.dumps({'props':{'pageProps':{'state':{'data':{'entity':entity}}}}})+'</script>'
    monkeypatch.setattr(s,'public_bytes',lambda url,*_:page.encode() if '/embed/' in url else cover.getvalue())
    repaired=owner.post('/studio/imports/'+jid+'/artwork',headers=h,json={})
    assert repaired.status_code==200 and 'imported' in repaired.get_json()['artworkMessage']
    with DbEngine.manager() as db:updated=db.execute(__import__('sqlalchemy').select(PlaylistTable)).scalar()
    assert updated.image!=row.image and updated.trackhashes==row.trackhashes
    again=owner.post('/studio/imports/'+jid+'/artwork',headers=h,json={})
    assert 'kept' in again.get_json()['artworkMessage']

    # Only explicitly resumed failed/missing work runs again, on the same playlist.
    owner.post('/studio/imports/'+jid+'/start',headers=h,json={'download':False,'retry':True})
    assert finished()['playlist']==row.id and PlaylistTable.count()==1
    # Accepted work recovers after restart; startup dispatch waits for loaded stores.
    stored=service.load(jid,principal(UserTable.get_by_id(users[0].id)));stored['status']='running';service.save(stored)
    replacement=s.ImportManager(app)
    assert replacement.load(jid,stored['owner'])['status']=='queued'
    replacement.resume_pending()
    for _ in range(200):
        if not replacement.events:break
        time.sleep(.025)
    assert not replacement.events and replacement.load(jid,stored['owner'])['status']=='partial'
    # A deleted/reused owner account cannot retain its old import capability.
    old=users[0];UserTable.update_one({'id':old.id,'extra':{'musicPrincipal':'0'*64}})
    assert owner.get('/studio/imports/'+jid,headers=h).status_code==401


def test_immediate_index_is_repeatable_and_keeps_play_history(tmp_path,monkeypatch):
    import wave
    from swingmusic.settings import Paths,Singleton
    from swingmusic.db.engine import DbEngine
    monkeypatch.setattr(Singleton,'_instances',{})
    monkeypatch.setattr(DbEngine,'_engine',None)
    Paths(config_parent=tmp_path/'private',client_dir=tmp_path/'client')
    from swingmusic.setup import run_setup
    run_setup()
    from swingmusic.config import UserConfig
    UserConfig().rootDirs=[tmp_path.as_posix()]
    from swingmusic.store.tracks import TrackStore
    monkeypatch.setattr(TrackStore,'trackhashmap',{})
    file=tmp_path/'Original fixture.wav'
    with wave.open(str(file),'wb') as output:
        output.setparams((1,2,8000,0,'NONE','not compressed'));output.writeframes(b'\0\0'*16000)
    from swingmusic.lib.watchdogg import add_track
    from swingmusic.db.libdata import TrackTable
    from sqlalchemy import select,update
    add_track(str(file));add_track(str(file))
    assert TrackTable.count()==1 and len(TrackStore.trackhashmap)==1
    with DbEngine.manager(commit=True) as db:
        db.execute(update(TrackTable).values(playcount=7,playduration=99,lastplayed=1234))
    add_track(str(file))
    with DbEngine.manager() as db:
        row=db.execute(select(TrackTable)).scalar()
        assert (row.playcount,row.playduration,row.lastplayed)==(7,99,1234)
