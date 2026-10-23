import {defineConfig} from 'vite';
import {fileURLToPath} from 'node:url';
export default defineConfig({base:'./',resolve:{alias:{'@':fileURLToPath(new URL('./src',import.meta.url))}},build:{outDir:'dist',emptyOutDir:true,target:'es2022'}});
