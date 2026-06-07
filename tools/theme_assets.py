# -*- coding: utf-8 -*-
"""공유 CSS/JS — 다크 럭스 디자인 시스템(BLUEPRINT 기준). build.py에서 임포트."""

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0b0b0e;--surface:#13131a;--surface-2:#1a1a23;--line:rgba(255,255,255,.08);
  --text:#f3f3f5;--muted:#9a9aa3;--dim:#6c6c75;
  --gold:#d6b274;--rose:#e9b8a7;--copper:#c98a6b;
  --grad:linear-gradient(135deg,#f4d29c 0%,#e9b8a7 45%,#c98a6b 100%);
  --grad-soft:linear-gradient(135deg,rgba(244,210,156,.14),rgba(201,138,107,.06));
}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);line-height:1.65;letter-spacing:-.01em;
  font-family:"Pretendard","Apple SD Gothic Neo","Noto Sans KR",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:inherit;text-decoration:none}
img{max-width:100%;display:block}
.serif,.note-num,.step .n{font-family:"Cormorant Garamond","Noto Serif KR",Georgia,serif;font-weight:300;font-style:italic}
.grad{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.wrap{max-width:1240px;margin:0 auto;padding:0 24px}
section.block{padding:96px 0}
.eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:11.5px;letter-spacing:.2em;
  text-transform:uppercase;color:var(--gold);font-weight:700}
.pulse{width:7px;height:7px;border-radius:50%;background:var(--rose);box-shadow:0 0 0 0 rgba(233,184,167,.6);animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(233,184,167,.55)}70%{box-shadow:0 0 0 9px rgba(233,184,167,0)}100%{box-shadow:0 0 0 0 rgba(233,184,167,0)}}
h2.sec{font-size:clamp(28px,4vw,46px);letter-spacing:-.03em;font-weight:800;margin:14px 0 10px}
.sec-lead{color:var(--muted);max-width:660px;font-size:15px}
/* header */
header{position:sticky;top:0;z-index:60;backdrop-filter:blur(14px);
  background:rgba(11,11,14,.78);border-bottom:1px solid var(--line)}
.nav{max-width:1240px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;gap:18px}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:18px;letter-spacing:-.02em}
.brand .mark{width:34px;height:34px;border-radius:10px;background:var(--grad);display:grid;place-items:center;
  color:#1a1208;font-weight:800;font-family:"Cormorant Garamond",serif;font-style:italic;font-size:20px}
.brand small{display:block;font-size:10.5px;letter-spacing:.16em;color:var(--gold);font-weight:700}
.menu{list-style:none;display:flex;align-items:center;gap:4px;margin-left:auto}
.menu>li{position:relative}
.menu>li>a{display:block;padding:10px 13px;font-size:14px;color:var(--text);border-radius:9px;font-weight:600}
.menu>li>a:hover{background:rgba(255,255,255,.05)}
.menu>li>a.active{color:var(--gold)}
.submenu{position:absolute;top:calc(100% + 6px);left:0;min-width:212px;list-style:none;padding:8px;
  background:linear-gradient(160deg,var(--surface),var(--surface-2));border:1px solid var(--line);
  border-radius:14px;box-shadow:0 20px 48px rgba(0,0,0,.45);opacity:0;visibility:hidden;transform:translateY(6px);
  transition:.22s;z-index:70}
.menu>li:hover>.submenu,.menu>li:focus-within>.submenu{opacity:1;visibility:visible;transform:none}
.submenu li{position:relative}
.submenu li a{display:block;padding:9px 12px;font-size:13.5px;color:var(--muted);border-radius:9px}
.submenu li a:hover{background:rgba(255,255,255,.05);color:var(--text)}
.submenu li.has-sub>a::after{content:"›";float:right;color:var(--dim);font-weight:700}
.submenu .sub2{position:absolute;top:-9px;left:calc(100% + 7px);transform:translateX(6px)}
.submenu li.has-sub:hover>.sub2,.submenu li.has-sub:focus-within>.sub2{opacity:1;visibility:visible;transform:none}
.cta-pill{margin-left:6px;padding:11px 18px!important;background:var(--grad);color:#1a1208!important;
  border-radius:999px;font-weight:800!important}
.toggle{display:none;margin-left:auto;background:none;border:1px solid var(--line);color:var(--text);
  font-size:20px;width:44px;height:44px;border-radius:11px;cursor:pointer}
/* hero */
.hero{position:relative;overflow:hidden;border-bottom:1px solid var(--line)}
.hero::before{content:"";position:absolute;inset:0;z-index:0;
  background:radial-gradient(60% 70% at 80% 10%,rgba(233,184,167,.16),transparent 60%),
             radial-gradient(50% 60% at 10% 90%,rgba(214,178,116,.12),transparent 60%),
             radial-gradient(40% 50% at 50% 50%,rgba(201,138,107,.08),transparent 70%)}
.hero-inner{position:relative;z-index:1;display:grid;grid-template-columns:1.12fr .88fr;gap:48px;
  align-items:center;max-width:1240px;margin:0 auto;padding:88px 24px}
.hero h1{font-size:clamp(36px,6vw,70px);font-weight:800;letter-spacing:-.038em;line-height:1.06;margin:18px 0}
.hero .lead{color:var(--muted);font-size:16px;max-width:520px;margin-bottom:26px}
.actions{display:flex;gap:12px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:8px;padding:14px 22px;border-radius:12px;font-weight:700;
  font-size:14.5px;transition:.25s;border:1px solid transparent}
.btn-primary{background:var(--grad);color:#1a1208}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 14px 34px rgba(201,138,107,.35)}
.btn-ghost{border-color:var(--line);color:var(--text)}
.btn-ghost:hover{border-color:rgba(244,210,156,.4);transform:translateY(-2px)}
.trust{margin-top:24px;display:flex;flex-wrap:wrap;gap:8px 18px;color:var(--muted);font-size:13px}
.trust b{color:var(--text)}
.hero-visual{position:relative}
.glass{position:relative;z-index:2;border-radius:20px;padding:26px;
  background:linear-gradient(160deg,rgba(255,255,255,.06),rgba(255,255,255,.02));
  border:1px solid rgba(255,255,255,.12);backdrop-filter:blur(20px);transform:rotate(1.5deg)}
.glass h3{font-size:13px;color:var(--gold);letter-spacing:.04em;margin-bottom:14px}
.glass h3 b{display:block;font-size:21px;color:var(--text);letter-spacing:-.02em;margin-top:4px}
.book-row{display:flex;justify-content:space-between;padding:11px 0;border-top:1px solid var(--line);font-size:14px}
.book-row span:first-child{color:var(--muted)}
.bk{display:block;text-align:center;margin-top:16px;padding:13px;border-radius:12px;background:var(--grad);color:#1a1208;font-weight:800}
.floating{position:absolute;z-index:3;padding:11px 14px;border-radius:12px;font-size:12px;font-weight:600;
  background:linear-gradient(160deg,var(--surface),var(--surface-2));border:1px solid var(--line);
  box-shadow:0 14px 34px rgba(0,0,0,.4)}
.fl-1{top:-18px;left:-14px;transform:rotate(-4deg)}
.fl-2{bottom:-16px;right:-10px;transform:rotate(3deg)}
.fl-1 .dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#6fe3a1;margin-right:6px}
/* marquee */
.marquee{overflow:hidden;border-bottom:1px solid var(--line);background:var(--surface)}
.marquee-track{display:flex;gap:0;white-space:nowrap;width:max-content;animation:scroll 34s linear infinite}
.marquee-track span{padding:14px 26px;color:var(--muted);font-size:13px;letter-spacing:.04em}
.marquee-track span::after{content:"·";margin-left:26px;color:var(--dim)}
@keyframes scroll{to{transform:translateX(-50%)}}
/* cards grid */
.grid{display:grid;gap:16px}
.g4{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.g2{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.card{padding:24px;border-radius:16px;border:1px solid var(--line);
  background:linear-gradient(135deg,var(--surface),var(--surface-2));transition:.3s}
.card:hover{transform:translateY(-4px);border-color:rgba(244,210,156,.28);box-shadow:0 18px 40px rgba(0,0,0,.3)}
.card .k{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--gold);font-weight:700}
.card h3{margin:10px 0 8px;font-size:19px;font-weight:800}
.card p{color:var(--muted);font-size:14px}
.card .more{display:inline-block;margin-top:14px;color:var(--rose);font-size:13.5px;font-weight:700}
.card:hover .more{transform:translateX(4px)}
/* note card */
.note-card{display:flex;gap:22px;padding:26px 28px;border-radius:18px;position:relative;overflow:hidden;
  background:linear-gradient(135deg,var(--surface),var(--surface-2));border:1px solid var(--line);transition:.3s}
.note-card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--grad);opacity:0;transition:.3s}
.note-card:hover::before{opacity:1}
.note-card:hover{transform:translateY(-2px);box-shadow:0 18px 44px rgba(0,0,0,.32);border-color:rgba(244,210,156,.28)}
.note-num{font-size:44px;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;flex-shrink:0;line-height:1}
.note-title{font-size:18px;font-weight:800;margin-bottom:10px}
.note-text{max-width:660px}
.note-text p{margin:0 0 9px;color:#c8c8d0;font-size:14.5px;line-height:1.78}
.note-stack{display:flex;flex-direction:column;gap:14px}
/* chips */
.chips{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}
.chip{padding:9px 14px;border-radius:999px;border:1px solid var(--line);background:var(--surface);
  font-size:12.5px;color:var(--muted)}
.chip b{color:var(--gold)}
/* price */
.price-card{padding:24px;border-radius:16px;border:1px solid var(--line);position:relative;overflow:hidden;
  background:linear-gradient(135deg,var(--surface),var(--surface-2));transition:.3s}
.price-card::after{content:"";position:absolute;left:0;right:0;top:0;height:2px;background:var(--grad);opacity:.5}
.price-card:hover{transform:translateY(-3px);border-color:rgba(244,210,156,.3)}
.price-card.best{border-color:rgba(244,210,156,.45)}
.best-badge{position:absolute;top:14px;right:14px;font-size:10.5px;font-weight:800;letter-spacing:.1em;
  padding:5px 10px;border-radius:999px;background:var(--grad);color:#1a1208}
.price-card .k{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);font-weight:700}
.price-card h3{margin:8px 0 6px;font-size:20px;font-weight:800}
.price-card>p{color:var(--muted);font-size:13.5px;margin-bottom:14px}
.time-rows>div{display:flex;justify-content:space-between;padding:9px 0;border-top:1px solid var(--line);font-size:14px}
.time-rows span:last-child{font-weight:700}
/* 코스별 기본 요금 메뉴 */
.pmenu{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin-top:28px}
.pmenu-card{position:relative;text-align:center;padding:36px 24px 26px;border-radius:18px;
  background:linear-gradient(135deg,var(--surface),var(--surface-2));border:1px solid var(--line);transition:.3s}
.pmenu-card:hover{transform:translateY(-4px);border-color:rgba(244,210,156,.3);box-shadow:0 18px 42px rgba(0,0,0,.32)}
.pmenu-card.best{border-color:rgba(244,210,156,.5);box-shadow:0 16px 42px rgba(201,138,107,.2)}
.pmenu-name{font-weight:800;font-size:17px;margin-bottom:16px}
.pmenu-price{font-size:clamp(30px,4vw,40px);font-weight:800;letter-spacing:-.035em;line-height:1}
.pmenu-price span{font-size:15px;font-weight:600;color:var(--muted);margin-left:3px;letter-spacing:0}
.pmenu-dur{color:var(--gold);font-size:13px;font-weight:700;margin-top:10px}
.pmenu-desc{color:var(--muted);font-size:13.5px;margin:8px 0 22px}
.pmenu-btn{display:block;padding:13px;border-radius:11px;border:1px solid var(--line);font-weight:700;font-size:14px;transition:.25s}
.pmenu-btn:hover{border-color:rgba(244,210,156,.5);transform:translateY(-1px)}
.pmenu-card.best .pmenu-btn{background:var(--grad);color:#1a1208;border-color:transparent}
.pmenu-badge{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:var(--grad);color:#1a1208;
  font-size:11.5px;font-weight:800;padding:5px 15px;border-radius:999px;box-shadow:0 6px 16px rgba(201,138,107,.35)}
.pmenu-note{margin-top:20px;color:var(--muted);font-size:13px}
.pmenu-note a{color:var(--gold);font-weight:700;white-space:nowrap}
@media(max-width:760px){.pmenu{grid-template-columns:1fr}}
/* faq */
details{border:1px solid var(--line);border-radius:14px;padding:0;margin-bottom:12px;
  background:linear-gradient(135deg,var(--surface),var(--surface-2));overflow:hidden}
summary{list-style:none;cursor:pointer;padding:18px 22px;font-weight:700;font-size:15px;
  display:flex;justify-content:space-between;align-items:center;gap:14px}
summary::-webkit-details-marker{display:none}
summary span{color:var(--gold);font-size:22px;transition:.25s;flex-shrink:0}
details[open] summary span{transform:rotate(45deg)}
details>div{padding:0 22px 20px;color:var(--muted);font-size:14.5px;line-height:1.78}
/* breadcrumb */
.crumb{font-size:12.5px;color:var(--dim);padding:18px 0}
.crumb a{color:var(--muted)}
.crumb a:hover{color:var(--gold)}
.crumb b{color:var(--text)}
/* review */
.review{padding:22px;border-radius:16px;border:1px solid var(--line);
  background:linear-gradient(135deg,var(--surface),var(--surface-2))}
.review .stars{color:var(--gold);font-size:13px;letter-spacing:2px}
.review p{margin:10px 0;font-size:14px;color:#c8c8d0;line-height:1.7}
.review .who{font-size:12.5px;color:var(--muted)}
/* cta band */
.cta-band{position:relative;overflow:hidden;text-align:center;padding:88px 24px;border-top:1px solid var(--line)}
.cta-band::before{content:"";position:absolute;inset:0;background:radial-gradient(50% 80% at 50% 0%,rgba(233,184,167,.16),transparent 60%)}
.cta-band>div{position:relative}
.cta-band h2{font-size:clamp(26px,4vw,42px);font-weight:800;letter-spacing:-.03em}
.cta-band p{color:var(--muted);margin:12px 0 24px}
/* footer */
.site-footer{border-top:1px solid var(--line);background:var(--surface);padding:64px 0 36px;font-size:13.5px}
.footer-grid{display:grid;grid-template-columns:1.4fr 1fr 1fr 1fr;gap:30px}
.footer-grid h4{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin-bottom:14px}
.footer-grid a{display:block;color:var(--muted);padding:5px 0}
.footer-grid a:hover{color:var(--text)}
.footer-brand b{font-size:17px}
.footer-brand p{color:var(--muted);margin-top:10px;max-width:280px;line-height:1.7}
.footer-ops{margin:34px 0;padding:22px;border-radius:14px;background:var(--grad-soft);
  border:1px solid var(--line);display:flex;flex-wrap:wrap;gap:14px 40px}
.footer-ops div b{color:var(--gold);display:block;font-size:11px;letter-spacing:.12em;margin-bottom:4px}
.company-info{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;color:var(--dim);font-size:12.5px;
  padding-top:24px;border-top:1px solid var(--line)}
.company-info b{color:var(--muted)}
.footer-policies{display:flex;flex-wrap:wrap;gap:8px 18px;margin:22px 0 14px}
.footer-policies a{color:var(--muted);font-size:12.5px}
.footer-bottom{color:var(--dim);font-size:12px;line-height:1.7;border-top:1px solid var(--line);padding-top:18px}
.legal-note{margin-top:8px;color:var(--dim)}
/* 콘텐츠 아티클 + 저자 표기(E-E-A-T) */
.byline{display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:18px;color:var(--dim);font-size:12.5px}
.byline span{display:inline-flex;align-items:center}
.byline span+span::before{content:"·";margin-right:16px;color:var(--dim)}
.byline .au{color:var(--muted);font-weight:700}
.article{max-width:760px}
.article h2{font-size:clamp(21px,3vw,29px);font-weight:800;letter-spacing:-.02em;margin:38px 0 12px}
.article h2:first-child{margin-top:8px}
.article h3{font-size:17px;font-weight:800;margin:20px 0 8px}
.article p{color:#c8c8d0;font-size:15px;line-height:1.85;margin:0 0 12px}
.article ul{margin:0 0 14px;padding-left:20px;color:#c8c8d0;font-size:15px;line-height:1.85}
.article li{margin-bottom:6px}
.article strong{color:var(--text)}
.data-box{margin:24px 0;padding:20px 22px;border-radius:14px;background:var(--grad-soft);border:1px solid var(--line)}
.data-box b{color:var(--gold);display:block;font-size:11px;letter-spacing:.14em;margin-bottom:8px;text-transform:uppercase}
.data-box p{color:var(--muted);font-size:13.5px;margin:0;line-height:1.8}
/* 다크 럭스 스파 — 지역/콘텐츠 페이지 (네이비 패널 + 골드 + 좌측 TOC) */
.lux-hero{position:relative;overflow:hidden;border-bottom:1px solid rgba(244,210,156,.14);
  background:radial-gradient(70% 120% at 88% -10%,rgba(233,184,167,.14),transparent 60%),
             linear-gradient(180deg,#0d1018,#0b0b0e);padding:54px 0 40px}
.lux-h1{font-size:clamp(30px,5vw,52px);font-weight:800;letter-spacing:-.03em;line-height:1.1;margin:14px 0 12px;color:#fff}
.lux-lead{color:#cfd2da;font-size:16.5px;line-height:1.8;max-width:760px}
.lux-body{background:linear-gradient(180deg,#0b0b0e,#0c0e15 40%,#0b0b0e)}
.lux-grid{display:grid;grid-template-columns:240px 1fr;gap:46px;align-items:start}
.toc{position:sticky;top:86px}
.toc-inner{border:1px solid rgba(244,210,156,.2);border-radius:16px;padding:18px 14px;
  background:linear-gradient(165deg,#10131f,#0a0c13);box-shadow:0 18px 40px rgba(0,0,0,.35)}
.toc-label{display:block;font-size:10.5px;letter-spacing:.2em;color:var(--gold);font-weight:800;text-transform:uppercase;margin:0 0 12px 8px}
.toc ul{list-style:none;margin:0;padding:0}
.toc li a{display:block;padding:8px 12px;font-size:13px;line-height:1.4;color:var(--muted);
  border-left:2px solid transparent;border-radius:0 8px 8px 0;transition:.2s}
.toc li a:hover{color:var(--text);background:rgba(255,255,255,.05)}
.toc li a.active{color:var(--gold);border-left-color:var(--gold);background:rgba(244,210,156,.09);font-weight:700}
.lux-main{min-width:0}
.lux-sec{position:relative;overflow:hidden;background:linear-gradient(165deg,#121626,#0c0e16);
  border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:28px 32px;margin-bottom:18px}
.lux-sec::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--grad)}
.lux-sec h2{font-size:clamp(20px,2.5vw,27px);font-weight:800;letter-spacing:-.02em;margin:0 0 14px;color:#fff}
.lux-sec h3{color:var(--gold);font-size:16.5px;font-weight:800;margin:20px 0 7px}
.lux-sec p{color:#e4e5ec;font-size:15.5px;line-height:1.9;margin:0 0 12px}
.lux-sec>ul{margin:6px 0 14px;padding:0;list-style:none}
.lux-sec>ul li{position:relative;padding:8px 0 8px 22px;color:#e4e5ec;font-size:15px;line-height:1.65;
  border-bottom:1px solid rgba(255,255,255,.06)}
.lux-sec>ul li::before{content:"";position:absolute;left:3px;top:15px;width:6px;height:6px;border-radius:50%;background:var(--grad)}
.lux-sec>ul li:last-child{border-bottom:none}
.lux-sec a{color:var(--rose);font-weight:600;border-bottom:1px solid rgba(233,184,167,.4)}
.lux-sec a:hover{color:var(--gold);border-bottom-color:var(--gold)}
.lux-sec strong{color:#fff}
.lux-sec .grid{margin-top:6px}
.lux-main .data-box{margin:4px 0 0;background:linear-gradient(135deg,rgba(244,210,156,.12),rgba(201,138,107,.05));
  border:1px solid rgba(244,210,156,.22)}
@media(max-width:980px){
  .lux-grid{grid-template-columns:1fr;gap:14px}
  .toc{position:static}
  .toc-inner{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:12px 14px}
  .toc-label{margin:0 4px 0 2px}
  .toc ul{display:flex;flex-wrap:wrap;gap:6px}
  .toc li a{border-left:none;border:1px solid var(--line);border-radius:999px;padding:6px 13px;font-size:12px}
  .toc li a.active{background:var(--grad);color:#1a1208;border-color:transparent}
  .lux-sec{padding:22px 20px}
}
/* 플로팅 전화예약 버튼 (전 페이지) */
.call-fab{position:fixed;right:20px;bottom:20px;z-index:90;display:inline-flex;align-items:center;gap:9px;
  padding:14px 20px 14px 16px;border-radius:999px;color:#fff;font-weight:800;font-size:14.5px;letter-spacing:-.01em;
  background:linear-gradient(135deg,#ffa23c,#ff7a18 55%,#f4600a);
  box-shadow:0 12px 30px rgba(255,122,24,.5);transition:transform .25s,box-shadow .25s}
.call-fab:hover{transform:translateY(-3px);box-shadow:0 16px 38px rgba(255,122,24,.6)}
.call-fab::before{content:"";position:absolute;inset:0;border-radius:999px;border:2px solid #ff7a18;
  animation:fabpulse 1.8s ease-out infinite;pointer-events:none}
.call-fab-ic{position:relative;display:grid;place-items:center;width:26px;height:26px;
  transform-origin:60% 60%;animation:fabring 1.5s ease-in-out infinite}
.call-fab-ic svg{width:21px;height:21px;fill:#fff}
.call-fab-tx{position:relative;white-space:nowrap}
.call-fab-tx small{display:block;font-size:11px;font-weight:700;opacity:.92;letter-spacing:.01em}
@keyframes fabring{0%,62%,100%{transform:rotate(0)}8%,26%{transform:rotate(-15deg)}17%,35%{transform:rotate(15deg)}}
@keyframes fabpulse{0%{transform:scale(1);opacity:.7}100%{transform:scale(1.55);opacity:0}}
@media(max-width:560px){.call-fab{right:14px;bottom:14px;padding:14px}.call-fab-tx{display:none}}
@media(prefers-reduced-motion:reduce){.call-fab-ic,.call-fab::before{animation:none}}
/* reveal */
.reveal{opacity:0;transform:translateY(20px);transition:.8s}
.reveal.in{opacity:1;transform:none}
/* perf */
#region,#process,#reviews,#about,#faq,.cta-band,.site-footer{content-visibility:auto;contain-intrinsic-size:auto 700px}
.card,.note-card,.review,.price-card{contain:layout style}
@media(hover:none){.glass,.floating{backdrop-filter:none}}
@media(prefers-reduced-motion:reduce){.marquee-track,.pulse{animation:none}.reveal{opacity:1;transform:none}}
@media(max-width:1100px){
  .toggle{display:block}
  .menu{position:fixed;inset:64px 0 auto 0;flex-direction:column;align-items:stretch;gap:2px;margin:0;
    padding:14px;background:var(--bg);border-bottom:1px solid var(--line);max-height:calc(100vh - 64px);
    overflow:auto;transform:translateY(-12px);opacity:0;visibility:hidden;transition:.25s}
  .menu.open{transform:none;opacity:1;visibility:visible}
  .menu>li>a{padding:13px 12px}
  .submenu,.submenu .sub2{position:static;opacity:1;visibility:visible;transform:none;box-shadow:none;
    background:transparent;border:none;padding:0 0 6px 12px;min-width:0;left:auto;top:auto}
  .submenu .sub2{padding-left:14px}
  .submenu li.has-sub>a::after{content:""}
  .cta-pill{text-align:center}
  .hero-inner{grid-template-columns:1fr;gap:36px}
  .hero-visual{max-width:420px}
  .footer-grid{grid-template-columns:1fr 1fr}
  .company-info{grid-template-columns:1fr 1fr}
}
@media(max-width:560px){
  .footer-grid,.company-info{grid-template-columns:1fr}
  .note-card{flex-direction:column;gap:12px}
  .hero-inner{padding:56px 24px}
}
"""

JS = """
(function(){
  var t=document.querySelector('.toggle'),m=document.getElementById('primary-menu');
  if(t&&m){t.addEventListener('click',function(){
    var o=m.classList.toggle('open');t.setAttribute('aria-expanded',o);});}
  document.addEventListener('keydown',function(e){if(e.key==='Escape'&&m){m.classList.remove('open');}});
  function idle(fn){if('requestIdleCallback'in window){requestIdleCallback(fn,{timeout:1500});}else{setTimeout(fn,1);}}
  idle(function(){
    if(!('IntersectionObserver'in window)){document.querySelectorAll('.reveal').forEach(function(el){el.classList.add('in');});return;}
    var io=new IntersectionObserver(function(es){es.forEach(function(e){
      if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});},{threshold:.12,rootMargin:'80px'});
    document.querySelectorAll('.reveal').forEach(function(el){io.observe(el);});
    var secs=[].slice.call(document.querySelectorAll('.lux-sec')),
        links=[].slice.call(document.querySelectorAll('.toc a'));
    if(secs.length&&links.length){
      var spy=new IntersectionObserver(function(es){es.forEach(function(e){
        if(e.isIntersecting){var id=e.target.id;
          links.forEach(function(a){a.classList.toggle('active',a.getAttribute('href')==='#'+id);});}});
      },{rootMargin:'-35% 0px -55% 0px'});
      secs.forEach(function(s){spy.observe(s);});
    }
  });
})();
"""
