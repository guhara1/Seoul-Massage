# -*- coding: utf-8 -*-
"""매거진 인덱스/카테고리 페이지에 클라이언트 페이지네이션을 주입한다.

- 카드는 HTML에 그대로 두어(색인 유지) 화면 표시만 9개씩 나눈다.
- CSS는 <style> 직전, JS는 </body> 직전에 삽입한다.
- 이미 적용된 페이지(id="mag-grid" 존재)는 건너뛴다.
"""
import os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GRID_OLD = '<div class="grid g3" style="margin-top:26px">'
GRID_NEW = '<div class="grid g3" id="mag-grid" style="margin-top:26px">'

CSS = """/* 매거진 페이지네이션 */
.pager{display:flex;justify-content:center;flex-wrap:wrap;gap:8px;margin:36px 0 4px}
.pager .pg{min-width:42px;height:42px;padding:0 13px;border-radius:11px;border:1px solid var(--line);
  background:linear-gradient(135deg,var(--surface),var(--surface-2));color:var(--muted);
  font-size:14px;font-weight:700;cursor:pointer;transition:.2s;display:inline-flex;align-items:center;justify-content:center}
.pager .pg:hover{border-color:rgba(244,210,156,.4);color:var(--text)}
.pager .pg.active{background:var(--grad);color:#1a1208;border-color:transparent}
.pager .pg.disabled{opacity:.35;cursor:default}
.pager .pg.disabled:hover{border-color:var(--line);color:var(--muted)}
.pager .pg.dots{border:none;background:none;cursor:default;min-width:auto;padding:0 4px}
"""

JS = """<script>
(function(){
  var grid=document.getElementById('mag-grid');
  if(!grid)return;
  var cards=[].slice.call(grid.children).filter(function(n){return n.tagName==='A';});
  var PER=9;
  if(cards.length<=PER)return;
  var pages=Math.ceil(cards.length/PER),cur=1;
  var pager=document.createElement('nav');
  pager.className='pager';pager.setAttribute('aria-label','매거진 페이지');
  grid.parentNode.insertBefore(pager,grid.nextSibling);
  function mk(label,page,o){o=o||{};
    var b=document.createElement(o.disabled?'span':'button');
    b.className='pg'+(o.active?' active':'')+(o.disabled?' disabled':'');
    b.textContent=label;
    if(o.aria)b.setAttribute('aria-label',o.aria);
    if(!o.disabled&&page){b.addEventListener('click',function(){cur=page;render();
      var y=grid.getBoundingClientRect().top+window.pageYOffset-90;
      window.scrollTo({top:y,behavior:'smooth'});});}
    pager.appendChild(b);
  }
  function render(){
    cards.forEach(function(c,i){
      var show=(i>=(cur-1)*PER&&i<cur*PER);
      c.style.display=show?'':'none';
      if(show)c.classList.add('in');
    });
    pager.innerHTML='';
    mk('‹',cur-1,{disabled:cur===1,aria:'이전'});
    for(var p=1;p<=pages;p++){
      if(p===1||p===pages||Math.abs(p-cur)<=1){mk(String(p),p,{active:p===cur});}
      else if(p===cur-2||p===cur+2){var d=document.createElement('span');d.className='pg dots';d.textContent='…';pager.appendChild(d);}
    }
    mk('›',cur+1,{disabled:cur===pages,aria:'다음'});
  }
  render();
})();
</script>
"""

targets = [os.path.join(ROOT, "magazine/index.html")]
targets += sorted(glob.glob(os.path.join(ROOT, "magazine/category/*/index.html")))

done = 0
for p in targets:
    s = open(p, encoding="utf-8").read()
    if 'id="mag-grid"' in s:
        print("  (이미 적용) " + os.path.relpath(p, ROOT)); continue
    if GRID_OLD not in s:
        print("  (그리드 없음) " + os.path.relpath(p, ROOT)); continue
    s = s.replace(GRID_OLD, GRID_NEW, 1)
    s = s.replace("</style>", CSS + "</style>", 1)
    s = s.replace("</body>", JS + "</body>", 1)
    open(p, "w", encoding="utf-8").write(s)
    done += 1
    print("  적용: " + os.path.relpath(p, ROOT))

print(f"\n총 {done}개 페이지에 페이지네이션 적용")
