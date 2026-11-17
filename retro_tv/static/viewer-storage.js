// Browser preferences are optional; blocked or full storage never prevents viewing.
window.viewerStorage={read(key,fallback=null){try{const v=localStorage.getItem('tv-master:'+key);return v===null?fallback:JSON.parse(v);}catch{return fallback;}},write(key,value){try{localStorage.setItem('tv-master:'+key,JSON.stringify(value));return true;}catch{return false;}}};
