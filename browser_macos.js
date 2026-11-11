/* Local Chrome automation through the browser's official Apple Events API. */
function run(argv) {
  try {
    var p = JSON.parse(argv[0]);
    var chrome = Application('Google Chrome');
    if (!chrome.running()) {
      if (p.action === 'windows') return JSON.stringify({ok:true, windows:[]});
      throw new Error('Open Google Chrome before capturing browser tabs.');
    }
    var windows = chrome.windows();
    if (p.action === 'windows') return JSON.stringify({ok:true, windows:windows.map(function(w) {
      return {id:w.id(), title:w.name() + ' — Google Chrome'};
    })});
    if (p.action === 'front') return JSON.stringify({ok:true, id:windows.length ? windows[0].id() : null});
    var win = windows.filter(function(w) {return w.id() === p.hwnd;})[0];
    if (!win) throw new Error('The selected browser window closed.');
    if (p.action === 'bounds') {
      var b = win.bounds();
      return JSON.stringify({ok:true, bounds:Array.isArray(b) ? b : [b.x,b.y,b.x+b.width,b.y+b.height]});
    }
    if (p.action === 'title') return JSON.stringify({ok:true, title:win.name() + ' — Google Chrome'});
    if (p.action === 'activate') { win.index = 1; chrome.activate(); return JSON.stringify({ok:true}); }
    if (p.action === 'tabs') return JSON.stringify({ok:true, original:win.activeTabIndex()-1, tabs:win.tabs().map(function(tab,i) {
      return {index:i, id:tab.id(), title:tab.title()};
    })});
    if (p.action === 'select_tab' || p.action === 'tab_selected') {
      var tabs = win.tabs();
      var index = tabs.findIndex(function(tab) { return tab.id() === p.tab_id; });
      if (index < 0) throw new Error('A tab closed during capture.');
      if (p.action === 'select_tab') { win.activeTabIndex = index+1; win.index=1; chrome.activate(); }
      return JSON.stringify({ok:true, selected:win.activeTabIndex() === index+1});
    }
    if (p.action === 'url') return JSON.stringify({ok:true, url:win.activeTab().url()});
    if (p.action === 'scroll') {
      var percent = Math.min(100, Math.max(0, Number(p.percent)));
      if (!isFinite(percent)) throw new Error('Invalid scroll position.');
      win.activeTab().execute({javascript:'(function(){var e=document.scrollingElement; if(!e)throw Error("Page not ready"); e.scrollTop=Math.max(0,e.scrollHeight-e.clientHeight)*'+percent+'/100;return true;})()'});
    }
    if (p.action === 'metrics' || p.action === 'scroll') {
      var value = win.activeTab().execute({javascript:'(function(){var e=document.scrollingElement;if(!e)throw Error("Page not ready");var total=e.scrollHeight,view=e.clientHeight,range=Math.max(0,total-view);return JSON.stringify({ok:true,scrollable:range>1,percent:range>1?e.scrollTop/range*100:-1,view:total?view/total*100:100});})()'});
      return JSON.stringify(JSON.parse(value));
    }
    throw new Error('Unknown action: ' + p.action);
  } catch (error) {return JSON.stringify({ok:false, error:String(error)});}
}
