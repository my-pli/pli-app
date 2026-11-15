/**
 * Pull the child's recent KidsNote albums (photos only, no videos) for the edge album.
 *
 * Uses the same reviewed KidsNote MCP modules and stored session as scripts/kidsnote-mcp.mjs,
 * but writes only under .tools/private-family/kidsnote-albums (mode 700/600): the HTTP MCP keeps
 * refusing arbitrary save_dir. Output: one folder per album plus albums.json
 * [{id, date, title, photos: [file names]}]. Faces are handled later by scripts/family_photos.py.
 *
 * usage: node scripts/kidsnote-album-sync.mjs [albums=10] [photosPerAlbum=6]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { setKeyDirs, callTool } from './kidsnote_mcp/server.mjs';
import { seedSession, api, download, photoName, photoUrl, kstDate } from './kidsnote_mcp/site.mjs';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const keys = path.join(root, '.tools/private/kidsnote');
const out = path.join(root, '.tools/private-family/kidsnote-albums');
const albums = Math.min(30, Math.max(1, Number(process.argv[2]) || 10));
const perAlbum = Math.min(12, Math.max(1, Number(process.argv[3]) || 6));

setKeyDirs([keys]);
const browser = JSON.parse(fs.readFileSync(path.join(keys, 'browser.json'), 'utf8'));
const cookie = browser.cookies.filter((c) => c.domain === 'kidsnote.com' || c.domain.endsWith('.kidsnote.com')).map((c) => `${c.name}=${c.value}`).join('; ');
if (!cookie) throw new Error('KIDSNOTE_SESSION_MISSING');
await seedSession(cookie);

fs.mkdirSync(out, { recursive: true, mode: 0o700 });
fs.chmodSync(out, 0o700);
const listing = await callTool('list_albums', { limit: albums });
const ids = [...listing.matchAll(/앨범 (\d+)\s*$/gm)].map((m) => m[1]);
if (!ids.length) throw new Error('NO_ALBUMS');

const result = [];
for (const id of ids) {
  const album = await api(`/v1_3/albums/${id}/`);
  const dir = path.join(out, id);
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  const photos = [];
  for (const [i, image] of (album.attached_images ?? []).slice(0, perAlbum).entries()) {
    try {
      const saved = await download(photoUrl(image), dir, photoName(image, i));
      fs.chmodSync(saved.path, 0o600);
      photos.push(path.basename(saved.path));
    } catch (error) {
      console.error(`album ${id} photo ${i + 1}: ${error.message}`);
    }
  }
  result.push({ id, date: kstDate(album.created), title: String(album.title ?? '').trim(), photos });
  console.log(JSON.stringify({ id, date: kstDate(album.created), photos: photos.length }));
}
const index = path.join(out, 'albums.json');
fs.writeFileSync(index, JSON.stringify(result, null, 1), { mode: 0o600 });
console.log(JSON.stringify({ albums: result.length, photos: result.reduce((n, a) => n + a.photos.length, 0) }));
