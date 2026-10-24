import {chromium,expect} from '@playwright/test';
import {spawn,spawnSync} from 'node:child_process';
import {randomBytes} from 'node:crypto';
import {mkdir,writeFile} from 'node:fs/promises';
const root=process.env.MY_MUSIC_QA_DATA,out=process.env.MY_MUSIC_QA_OUTPUT,python=process.env.MY_MUSIC_QA_PYTHON,source=process.env.MY_MUSIC_QA_SOURCE,client=process.env.MY_MUSIC_QA_CLIENT;
if(!root?.startsWith('C:/Projects/.cache/music-spotify-20261024/')||!out||!python||!source||!client)throw Error('Use explicit fresh task-owned fixture paths');
await mkdir(out,{recursive:true});
const secret=randomBytes(24).toString('hex'),origin='http://localhost:39124/music',errors=[],checks=[];
const child=spawn(python,[source+'/tests/listening_fixture.py','--root',root,'--client',client,'--spotify-fixture'],{env:{...process.env,PYTHONPATH:source+'/src',MY_MUSIC_FIXTURE_SECRET:secret},windowsHide:true,stdio:['ignore','pipe','pipe']});let log='',browser,page;
child.stdout.on('data',b=>log=(log+b).slice(-20000));child.stderr.on('data',b=>log=(log+b).slice(-20000));
try{
 let ready=false;for(let i=0;i<120;i++){if(child.exitCode!==null)throw Error('Fixture stopped: '+log);try{if((await fetch(origin+'/onboarding-data')).ok){ready=true;break}}catch{}await new Promise(r=>setTimeout(r,500))}if(!ready)throw Error('Fixture did not start: '+log);
 browser=await chromium.launch({channel:'msedge',headless:true,args:['--autoplay-policy=no-user-gesture-required']});
 const context=await browser.newContext({viewport:{width:1440,height:940},hasTouch:true});page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.goto(origin+'/fixture/login?'+new URLSearchParams({account:'Alex',key:secret}));
 await page.getByRole('button',{name:'Import playlist',exact:true}).click();await expect(page.getByRole('heading',{name:'Import from Spotify',exact:true})).toBeVisible();
 await page.getByLabel('Spotify playlist link',{exact:true}).fill('https://evil.test/playlist/no');await page.getByRole('button',{name:'Preview playlist',exact:true}).click();await expect(page.getByRole('alert')).toContainText('open.spotify.com');
 await page.getByLabel('Spotify playlist link',{exact:true}).fill('https://open.spotify.com/playlist/'+'a'.repeat(22));await page.getByRole('button',{name:'Preview playlist',exact:true}).click();await expect(page.getByRole('heading',{name:'Sunrise essentials',exact:true})).toBeVisible();await expect(page.locator('.import-track')).toHaveCount(2);await expect(page.locator('.import-metric').filter({hasText:'Ready to play'})).toContainText('1');
 await page.screenshot({path:out+'/spotify-preview-desktop.png'});checks.push('Paste-link validation, metadata preview and existing-library reuse');
 await page.getByRole('button',{name:'Import and download',exact:true}).click();await expect(page.getByRole('button',{name:'Stop import',exact:true})).toBeVisible();await page.getByRole('button',{name:'Stop import',exact:true}).click();await expect(page.locator('.import-summary-heading .import-badge')).toHaveText('cancelled',{timeout:15000});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:out+'/spotify-cancelled-phone.png'});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 await page.getByRole('button',{name:'Resume unfinished songs',exact:true}).click();await expect(page.locator('.import-summary-heading .import-badge')).toHaveText('complete',{timeout:30000});await expect(page.locator('.import-metric').filter({hasText:'Ready to play'})).toContainText('2');await page.screenshot({path:out+'/spotify-complete-phone.png'});checks.push('Cancel during a synthetic download, keep existing songs, resume into the same playlist and complete');
 await page.getByRole('button',{name:'Open playlist',exact:true}).click();await expect(page.locator('.song-row')).toHaveCount(2);await page.locator('.song-title').filter({hasText:'New Sunrise'}).click();await expect.poll(()=>page.locator('audio').evaluate(a=>a.currentTime)).toBeGreaterThan(0);checks.push('Downloaded synthetic MP3 indexes and plays from the imported playlist');
 await page.getByRole('button',{name:'Your Library',exact:true}).click();await page.getByRole('button',{name:'Import playlist',exact:true}).filter({visible:true}).click();await expect(page.getByRole('heading',{name:'Import from Spotify',exact:true})).toBeVisible();await page.reload();await expect(page.locator('.import-summary-heading .import-badge')).toHaveText('complete');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();checks.push('Mobile Library entry, reload persistence and no horizontal overflow');
 await page.setViewportSize({width:1440,height:940});await page.screenshot({path:out+'/spotify-complete-desktop.png'});expect(errors).toEqual([]);
 await writeFile(out+'/spotify-browser-acceptance.json',JSON.stringify({checks,errors,syntheticOnly:true,viewports:[[1440,940],[390,844]]},null,2));console.log('Spotify import browser checks passed');
}catch(e){await page?.screenshot({path:out+'/spotify-failure.png'}).catch(()=>{});await writeFile(out+'/spotify-failure.log',String(e)+'\n'+log);throw e}
finally{await browser?.close();spawnSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});await writeFile(out+'/fixture-process.json',JSON.stringify({pid:child.pid,root,stopped:true}));}
