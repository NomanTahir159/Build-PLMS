// Windows integration test: real WebView2 + native NSIS-style controls, no install.
#define PLMS_HOST_TEST
#include "plms-theme.cpp"
#include <shlwapi.h>
#include <cstdio>
#include <cwchar>

int lastCommand=0;
LRESULT CALLBACK hostProc(HWND w,UINT m,WPARAM a,LPARAM l){if(m==WM_COMMAND){lastCommand=LOWORD(a);return 0;}return DefWindowProcW(w,m,a,l);}
bool pump(const std::function<bool()>& done,DWORD timeout=30000){DWORD begin=GetTickCount();while(!done()&&GetTickCount()-begin<timeout){MSG msg{};while(PeekMessageW(&msg,nullptr,0,0,PM_REMOVE)){TranslateMessage(&msg);DispatchMessageW(&msg);}MsgWaitForMultipleObjects(0,nullptr,FALSE,10,QS_ALLINPUT);}return done();}
bool check(bool ok,const char* label){if(!ok)std::fprintf(stderr,"FAIL: %s\n",label);return ok;}
std::wstring evaluate(const Shared& c,const std::wstring& script){
    bool done=false;std::wstring value;
    auto callback=new Callback<ICoreWebView2ExecuteScriptCompletedHandler,HRESULT,LPCWSTR>([&](HRESULT result,LPCWSTR text)->HRESULT{if(SUCCEEDED(result)&&text)value=text;done=true;return S_OK;});
    HRESULT result=c->web->ExecuteScript(script.c_str(),callback);callback->Release();if(FAILED(result)||!pump([&]{return done;}))return L"evaluation failed";return value;
}
bool capture(const Shared& c,const std::wstring& path){
    ComPtr<IStream> stream;
    if(FAILED(SHCreateStreamOnFileEx(path.c_str(),STGM_CREATE|STGM_WRITE|STGM_SHARE_EXCLUSIVE,FILE_ATTRIBUTE_NORMAL,TRUE,nullptr,stream.put())))return false;
    bool done=false,ok=false;auto callback=new Callback<ICoreWebView2CapturePreviewCompletedHandler,HRESULT>([&](HRESULT result)->HRESULT{ok=SUCCEEDED(result);done=true;return S_OK;});
    HRESULT result=c->web->CapturePreview(COREWEBVIEW2_CAPTURE_PREVIEW_IMAGE_FORMAT_PNG,stream.get(),callback);callback->Release();return SUCCEEDED(result)&&pump([&]{return done;})&&ok;
}
int wmain(int argc,wchar_t** argv){
    const std::wstring base=argc>1?argv[1]:L".";
    if(!RuntimeAvailable(base.c_str())){std::fprintf(stderr,"WebView2 Runtime is required for native integration checks.\n");return 2;}
    INITCOMMONCONTROLSEX common{sizeof(common),ICC_STANDARD_CLASSES|ICC_PROGRESS_CLASS};InitCommonControlsEx(&common);
    WNDCLASSW cls{};cls.lpfnWndProc=hostProc;cls.hInstance=GetModuleHandleW(nullptr);cls.lpszClassName=L"PLMS_HTML_Integration";RegisterClassW(&cls);
    HWND window=CreateWindowW(cls.lpszClassName,L"PLMS",WS_OVERLAPPEDWINDOW,0,0,952,998,nullptr,nullptr,cls.hInstance,nullptr);
    HWND next=CreateWindowW(L"BUTTON",L"Next",WS_CHILD|WS_VISIBLE,0,0,20,20,window,reinterpret_cast<HMENU>(IDOK),nullptr,nullptr);
    HWND cancel=CreateWindowW(L"BUTTON",L"Cancel",WS_CHILD|WS_VISIBLE,20,0,20,20,window,reinterpret_cast<HMENU>(IDCANCEL),nullptr,nullptr);
    HWND page=CreateWindowW(L"#32770",L"",WS_CHILD|WS_VISIBLE,0,100,600,400,window,nullptr,nullptr,nullptr);
    HWND folder=CreateWindowW(L"EDIT",L"C:\\Program Files\\Medicsoft\\PLMS",WS_CHILD|WS_VISIBLE,0,0,300,30,page,nullptr,nullptr,nullptr);
    HWND desktop=CreateWindowW(L"BUTTON",L"",WS_CHILD|BS_AUTOCHECKBOX,0,40,30,30,page,nullptr,nullptr,nullptr);
    HWND launch=CreateWindowW(L"BUTTON",L"",WS_CHILD|BS_AUTOCHECKBOX,40,40,30,30,page,nullptr,nullptr,nullptr);
    HWND repair=CreateWindowW(L"BUTTON",L"",WS_CHILD|BS_AUTORADIOBUTTON,0,80,30,30,page,nullptr,nullptr,nullptr);
    HWND uninstall=CreateWindowW(L"BUTTON",L"",WS_CHILD|BS_AUTORADIOBUTTON,40,80,30,30,page,nullptr,nullptr,nullptr);
    HWND exit=CreateWindowW(L"BUTTON",L"",WS_CHILD|BS_AUTORADIOBUTTON,80,80,30,30,page,nullptr,nullptr,nullptr);
    HWND remove=CreateWindowW(L"BUTTON",L"",WS_CHILD|BS_AUTOCHECKBOX,120,80,30,30,page,nullptr,nullptr,nullptr);
    HWND bar=CreateWindowW(PROGRESS_CLASSW,L"",WS_CHILD,0,120,300,20,page,reinterpret_cast<HMENU>(1004),nullptr,nullptr);
    bool ok=check(window&&next&&cancel&&page&&folder&&bar,"native test controls");
    Configure(window,(base+L"\\plms-dialog.html").c_str());BindPage(window,page);
    BindOption(window,1,folder);BindOption(window,2,desktop);BindOption(window,3,launch);BindOption(window,4,repair);BindOption(window,5,uninstall);BindOption(window,6,exit);BindOption(window,7,remove);
    setCheck(desktop,true);setCheck(launch,true);setCheck(repair,true);Layout(window,0);
    ok&=check(pump([&]{auto c=context(window);return c&&(c->rendered||FAILED(c->lastError));},65000),"approved HTML ready before window reveal");
    auto c=context(window);if(!c||!c->ready||!c->rendered){
        if(c){std::fprintf(stderr,"Startup stage: environment=%d controller=%d web=%d navigation=%d ready=%d model=%d rendered=%d HRESULT=0x%08lX\n",static_cast<int>(!!c->environment),static_cast<int>(!!c->controller),static_cast<int>(!!c->web),c->navigated,c->ready,c->hasState,c->rendered,static_cast<unsigned long>(c->lastError));
            if(c->web){auto diagnostic=evaluate(c,LR"JS(JSON.stringify({url:location.href,ready:document.readyState,bridge:!!window.chrome?.webview,app:!!window.plmsInstaller,images:Array.from(document.images).map(i=>({complete:i.complete,width:i.naturalWidth}))}))JS");std::fwprintf(stderr,L"Document diagnostics: %ls\n",diagnostic.c_str());}}
        Detach(window);DestroyWindow(window);return 1;
    }
    PWSTR expectedLocalAppData=nullptr;
    HRESULT profile=SHGetKnownFolderPath(FOLDERID_LocalAppData,0,nullptr,&expectedLocalAppData);
    ok&=check(SUCCEEDED(profile)&&expectedLocalAppData&&c->userDataFolder.find(std::wstring(expectedLocalAppData)+L"\\Medicsoft\\PLMS\\InstallerWebView")==0,"WebView2 profile is in per-user Local AppData");
    CoTaskMemFree(expectedLocalAppData);
    ok&=check(c->userDataFolder.find(base+L"\\")==std::wstring::npos,"WebView2 profile is outside installer extraction resources");
    HANDLE profileProbe=CreateFileW((c->userDataFolder+L"\\plms-smoke-write-probe").c_str(),GENERIC_WRITE,0,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_TEMPORARY|FILE_FLAG_DELETE_ON_CLOSE,nullptr);
    ok&=check(profileProbe!=INVALID_HANDLE_VALUE,"installer browser profile is writable");
    if(profileProbe!=INVALID_HANDLE_VALUE)CloseHandle(profileProbe);
    const wchar_t* states[]={L"install",L"installing",L"installed",L"maintenance",L"uninstall",L"uninstalling",L"uninstalled"};
    CreateDirectoryW((base+L"\\screenshots").c_str(),nullptr);
    for(int state=0;state<7;++state){
        Layout(window,state);
        // Simulate NSIS repositioning/showing its native page after the callback.
        SetWindowPos(page,HWND_TOP,0,140,600,400,SWP_SHOWWINDOW);
        ShowWindow(next,SW_SHOW);ShowWindow(cancel,SW_SHOW);
        const std::wstring expected=L"\""+std::wstring(states[state])+L"\"";
        ok&=check(pump([&]{return evaluate(c,L"window.plmsInstaller.state.state")==expected;},10000),"HTML state matches NSIS page");
        std::wstring verify=LR"JS((()=>{try{
          const q=s=>document.querySelector(s),r=q('.setup-window').getBoundingClientRect(),logo=q('.product-logo').getBoundingClientRect(),brand=q('.product-subtitle').getBoundingClientRect(),footer=q('.setup-footer').getBoundingClientRect();
          if(Math.abs(logo.width-logo.height)>0.1)throw Error('logo proportion');
          if(!q('.product-logo').complete||!q('.product-logo').naturalWidth)throw Error('missing logo');
          if(r.left<-1||r.top<-1||r.right>innerWidth+1||r.bottom>innerHeight+1)throw Error('window clipping');
          if(q('.success')){const row=q('.success').getBoundingClientRect(),mark=q('.success-mark').getBoundingClientRect();if(row.top<brand.bottom||mark.bottom>footer.top)throw Error('completion overlap');}
          if(getComputedStyle(q('.setup-heading')).height!=='126px')throw Error('header geometry');
          return 'pass';
        }catch(e){return String(e.message)}})())JS";
        ok&=check(evaluate(c,verify)==L"\"pass\"","approved geometry and complete logo");
        for(HWND child=GetWindow(window,GW_CHILD);child;child=GetWindow(child,GW_HWNDNEXT))if(child!=c->host)ok&=check(!IsWindowVisible(child),"native page cannot cover HTML");
        if(state==1||state==5){SendMessageW(bar,PBM_SETRANGE32,0,1000);SendMessageW(bar,PBM_SETPOS,680,0);progress(c);ok&=check(pump([&]{return evaluate(c,L"window.plmsInstaller.state.percent")==L"68";}),"actual engine percentage");}
        ok&=check(capture(c,base+L"\\screenshots\\"+states[state]+L".png"),"capture actual WebView2 state");
    }
    SetDataChoice(window,1);Layout(window,6);
    ok&=check(pump([&]{return evaluate(c,L"document.querySelector('.success small')?.textContent.includes('removed')")==L"true";}),"deletion result reflected accurately");
    Layout(window,0);pump([&]{return evaluate(c,L"window.plmsInstaller.state.state")==L"\"install\"";});lastCommand=0;
    evaluate(c,LR"JS((()=>{document.querySelector('#plms-folder').value='C:\\Medicsoft\\PLMS';document.querySelector('#plms-desktop').checked=false;document.querySelector('.glass.primary').click();return true})())JS");
    ok&=check(pump([&]{return lastCommand==IDOK;}),"Install advances native engine");
    ok&=check(text(folder)==L"C:\\Medicsoft\\PLMS"&&!checked(desktop)&&checked(launch),"native folder and options receive HTML values");
    Layout(window,4);pump([&]{return evaluate(c,L"window.plmsInstaller.state.state")==L"\"uninstall\"";});lastCommand=0;
    evaluate(c,L"document.querySelector('#plms-delete-data').checked=true;document.querySelector('.glass.danger').click();true");
    ok&=check(pump([&]{return lastCommand==IDOK;})&&checked(remove),"HTML removal choice reaches native confirmation");
    const auto blockedBefore=c->blockedNavigations;
    c->web->Navigate(L"https://example.invalid/plms-navigation-must-be-blocked");
    ok&=check(pump([&]{return c->blockedNavigations>blockedBefore;}),"subsequent navigation is canceled");
    ok&=check(evaluate(c,L"location.href==='about:blank' && !!window.plmsInstaller")==L"true","approved document remains loaded after blocked navigation");
    Detach(window);DestroyWindow(window);if(ok)std::puts("Seven approved HTML states, live progress, native options and overlap checks passed.");return ok?0:1;
}
