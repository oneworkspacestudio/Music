"""Apply the small prefix/SSO adapter to upstream webclient v3.0.0 before Vite build."""
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1])
def patch(name, old, new):
    path = root / name
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Unsupported webclient source: {name}")
    path.write_text(text.replace(old, new), encoding="utf-8")

patch("src/config.ts", "return ''", "return window.location.pathname.replace(/\\/$/, '')")
patch("src/router/index.ts", "createWebHashHistory(import.meta.env.BASE_URL)", "createWebHashHistory(window.location.pathname + window.location.search)")
for file in ["src/stores/events.ts", "src/stores/tracker.ts", "src/stores/player.ts"]:
    path = root / file
    text = path.read_text(encoding="utf-8")
    text = text.replace("new URL('/workers/sse-events.js', import.meta.url)", "new URL('./workers/sse-events.js', window.location.href)")
    text = text.replace('new Worker("/workers/logtrack.js")', 'new Worker(new URL("./workers/logtrack.js", window.location.href))')
    text = text.replace("new Worker('/workers/silence.js')", "new Worker(new URL('./workers/silence.js', window.location.href))")
    path.write_text(text, encoding="utf-8")
for file in (root / "public/workers").glob("*.js"):
    text = file.read_text(encoding="utf-8")
    text = text.replace(": location.origin", ": new URL('../', location.href).href.replace(/\\/$/, '')")
    file.write_text(text, encoding="utf-8")
patch("src/requests/useAxios.ts", "useModal().showLoginModal()", "if (error.response?.data?.login) window.location.assign(new URL('./auth/myaccounts/login', window.location.href).href); else useModal().showLoginModal()")
# Authentication navigations must reach the server, never the offline SPA shell.
patch("vite.config.ts", 'registerType: "autoUpdate",', r'registerType: "autoUpdate", workbox: { navigateFallback: null },')
# Scope the installable app to its own directory in both standalone and suite mode.
patch("vite.config.ts", 'start_url: "/"', 'start_url: "./", scope: "./"')
patch("vite.config.ts", 'url: "/#/', 'url: "./#/')

assets = Path(__file__).resolve().parents[1] / "src/swingmusic/assets"
for file in (root / "src/assets/icons/logos").glob("*.svg"):
    shutil.copyfile(assets / "my_music.svg", file)
for name in ["logo.svg", "logo-fill.light.svg", "favicon.svg"]:
    shutil.copyfile(assets / "my_music.svg", root / "public" / name)
for size in [192, 512]:
    shutil.copyfile(assets / f"my_music-{size}.png", root / "public" / f"pwa-{size}x{size}.png")
shutil.copyfile(assets / "logo-fill.light.ico", root / "public/favicon.ico")
patch("index.html", "<title>Swing Music</title>", '<title>My Music</title><link rel="icon" type="image/svg+xml" href="./favicon.svg">')
patch("src/components/Logo.vue", "<LogoSvg />", '<img :src="musicLogo" alt="" width="32" height="32" />')
patch("src/components/Logo.vue", 'import LogoSvg from "@/assets/icons/logos/logo-fill.light.svg";', 'import musicLogo from "@/assets/icons/logos/logo-fill.light.svg?url";')
for name, size in [("nav/NavBar.vue", 32), ("nav/NavSidenav.vue", 24), ("Onboarding/Welcome.vue", 96)]:
    patch("src/components/" + name, "<LogoSvg />", f'<img :src="musicLogo" alt="" width="{size}" height="{size}" style="object-fit:contain;flex:none" />')
    patch("src/components/" + name, "import LogoSvg from '@/assets/icons/logos/logo-fill.light.svg'", "import musicLogo from '@/assets/icons/logos/logo-fill.light.svg?url'")
patch("src/components/modals/settings/custom/Pairing.vue", "image: '/logo-fill.light.svg'", "image: new URL('./logo-fill.light.svg', window.location.href).href")

patch("src/views/HomeView/main.vue", "getGreetings(auth.user.username)", "getGreetings(auth.user.firstname || auth.user.username)")
# Use the canonical endpoint directly, including for clients that cached an old
# permanent redirect before the reverse proxy preserved the mounted prefix.
patch("src/requests/home.ts", "paths.api.home.base + '?limit='", "paths.api.home.base + '/?limit='")
# The preserved standalone settings route requires a title for every category.
patch("src/settings/general/index.ts", "// title: 'General',", "title: 'General',")
patch("src/settings/index.ts", "export default [general, profile, pairing, accounts, library, audio, plugins, about]", "const categories = [general, profile, pairing, accounts, library, audio, plugins, about];\nconst names = ['General', 'Profile', 'Pairing', 'Accounts', 'Library', 'Audio', 'Plugins', 'About'];\ncategories.forEach((category, i) => { if (!category.title) category.title = names[i] });\nexport default categories")

# The PWA caches its own index rather than the proxy-injected HTML. Keep the
# suite switcher on that shell too; standalone root installations do not load it.
patch("index.html", "</body>", '<script>if(location.pathname.startsWith("/music/")){const s=document.createElement("script");s.src="/_workspace/navigation.js";s.defer=true;document.body.append(s)}</script></body>')
