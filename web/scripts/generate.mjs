import {parse,compileReact} from '@codedia/parser';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
await mkdir('src/generated',{recursive:true});
await writeFile('src/generated/Listening.tsx',compileReact(parse(await readFile('src/Listening.aui','utf8'))));
await writeFile('src/generated/Imports.tsx',compileReact(parse(await readFile('src/Imports.aui','utf8'))));
