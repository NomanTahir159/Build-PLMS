const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const html=fs.readFileSync(path.resolve(__dirname,'../../src/System/index.html'),'utf8');
assert(!html.includes('id="plms-context-menu-script"'),'Retired custom context menu must not replace native editing actions');
assert(!/addEventListener\(\s*['"]contextmenu['"]/.test(html),'Native context menu must remain available');
assert(!/oncontextmenu\s*=/.test(html),'Inline context-menu suppression must be absent');
console.log('Native right-click context menu preserved.');
