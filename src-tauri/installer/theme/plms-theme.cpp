// Approved HTML/CSS is the only dialog renderer. NSIS remains the install engine.
#define NOMINMAX
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <shobjidl.h>
#include <shlobj.h>
#include <WebView2.h>
#include <algorithm>
#include <atomic>
#include <functional>
#include <memory>
#include <string>
#include <vector>
#ifdef PLMS_HOST_TEST
#include <cstdio>
#endif
#include "webview2-callback-ids.h"

namespace {
constexpr UINT_PTR SubclassId=0x504c4d53;
constexpr UINT SyncMessage=WM_APP+0x537;
constexpr UINT_PTR StartupTimer=SubclassId+1;
constexpr int HtmlHostId=0x7f53;
HMODULE loader=nullptr;

template<class T> class ComPtr {
    T* p=nullptr;
public:
    ~ComPtr(){reset();}
    void reset(T* value=nullptr){if(value)value->AddRef();if(p)p->Release();p=value;}
    T** put(){reset();return &p;}
    T* get()const{return p;}
    T* operator->()const{return p;}
    explicit operator bool()const{return p!=nullptr;}
};
template<class I,class... A> class Callback final:public I {
    std::atomic<ULONG> refs{1};
    std::function<HRESULT(A...)> fn;
public:
    explicit Callback(std::function<HRESULT(A...)> f):fn(std::move(f)){}
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID id,void** out)override{
        if(!out){return E_POINTER;}*out=nullptr;
        if(IsEqualIID(id,IID_IUnknown)||IsEqualIID(id,callbackId<I>())){*out=static_cast<I*>(this);AddRef();return S_OK;}
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef()override{return ++refs;}
    ULONG STDMETHODCALLTYPE Release()override{ULONG value=--refs;if(!value)delete this;return value;}
    HRESULT STDMETHODCALLTYPE Invoke(A... args)override{return fn(args...);}
};
struct Context {
    HWND window=nullptr,host=nullptr,page=nullptr,progress=nullptr;
    HWND controls[9]{};
    int state=0,percent=0;
    unsigned int blockedNavigations=0;
    HRESULT lastError=S_OK;
    bool navigated=false,hasState=false,ready=false,rendered=false,detached=false,remove=false,desktop=true,launch=true,canRepair=true,comInitialized=false;
    std::wstring folder,maintenance=L"repair",userDataFolder;
    ComPtr<ICoreWebView2Environment> environment;
    ComPtr<ICoreWebView2Controller> controller;
    ComPtr<ICoreWebView2> web;
    ~Context(){if(controller)controller->Close();if(comInitialized)CoUninitialize();}
};
using Shared=std::shared_ptr<Context>;
LRESULT CALLBACK windowProc(HWND,UINT,WPARAM,LPARAM,UINT_PTR,DWORD_PTR);
Shared context(HWND window){DWORD_PTR ref{};if(!GetWindowSubclass(window,windowProc,SubclassId,&ref))return {};return *reinterpret_cast<Shared*>(ref);}
std::wstring directory(const std::wstring& path){auto i=path.find_last_of(L"\\/");return i==std::wstring::npos?L".":path.substr(0,i);}
std::wstring json(const std::wstring& text){
    std::wstring out=L"\"";const wchar_t* digits=L"0123456789abcdef";
    for(wchar_t c:text){if(c==L'\\'||c==L'"'){out+=L'\\';out+=c;}else if(c<32){out+=L"\\u00";out+=digits[(c>>4)&15];out+=digits[c&15];}else out+=c;}
    return out+L"\"";
}
std::wstring readUtf8(const std::wstring& path){
    HANDLE file=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return {};
    DWORD length=GetFileSize(file,nullptr),read=0;if(length==INVALID_FILE_SIZE||length>1024*1024){CloseHandle(file);return {};}
    std::string bytes(length,'\0');BOOL ok=ReadFile(file,bytes.data(),length,&read,nullptr);CloseHandle(file);if(!ok||read!=length)return {};
    int count=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,bytes.data(),static_cast<int>(bytes.size()),nullptr,0);
    if(!count){return {};}std::wstring result(static_cast<size_t>(count),L'\0');
    MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,bytes.data(),static_cast<int>(bytes.size()),result.data(),count);return result;
}
std::wstring text(HWND control){if(!IsWindow(control))return {};int count=GetWindowTextLengthW(control);std::vector<wchar_t> value(static_cast<size_t>(count)+1);GetWindowTextW(control,value.data(),count+1);return value.data();}
bool checked(HWND control){return IsWindow(control)&&SendMessageW(control,BM_GETCHECK,0,0)==BST_CHECKED;}
void setCheck(HWND control,bool value){if(IsWindow(control))SendMessageW(control,BM_SETCHECK,value?BST_CHECKED:BST_UNCHECKED,0);}
void post(const Shared& c,const std::wstring& value){if(!c->detached&&c->ready&&c->navigated&&c->web)c->web->PostWebMessageAsJson(value.c_str());}
void model(const Shared& c){
    static const wchar_t* states[]={L"install",L"installing",L"installed",L"maintenance",L"uninstall",L"uninstalling",L"uninstalled"};
    std::wstring value=L"{\"state\":"+json(states[c->state])+L",\"percent\":"+std::to_wstring(c->percent)+L",\"folder\":"+json(c->folder);
    value+=L",\"desktop\":"+std::wstring(c->desktop?L"true":L"false")+L",\"launch\":"+(c->launch?L"true":L"false");
    value+=L",\"remove\":"+std::wstring(c->remove?L"true":L"false")+L",\"canRepair\":"+(c->canRepair?L"true":L"false")+L",\"maintenance\":"+json(c->maintenance)+L"}";
    post(c,value);
}
// Prevent a late native ShowWindow/SetWindowPos from covering the HTML surface.
LRESULT CALLBACK nativeChildProc(HWND child,UINT message,WPARAM a,LPARAM l,UINT_PTR,DWORD_PTR){
    if(message==WM_WINDOWPOSCHANGING){auto position=reinterpret_cast<WINDOWPOS*>(l);position->flags&=~SWP_SHOWWINDOW;position->flags|=SWP_HIDEWINDOW;}
    if(message==WM_NCDESTROY)RemoveWindowSubclass(child,nativeChildProc,SubclassId);
    return DefSubclassProc(child,message,a,l);
}
void hideChild(HWND child){
    if(GetDlgCtrlID(child)==HtmlHostId||!(GetWindowLongPtrW(child,GWL_STYLE)&WS_CHILD))return;
    SetWindowSubclass(child,nativeChildProc,SubclassId,0);ShowWindow(child,SW_HIDE);
}
void sync(const Shared& c){
    if(c->detached||!IsWindow(c->window))return;
    for(HWND child=GetWindow(c->window,GW_CHILD);child;child=GetWindow(child,GW_HWNDNEXT))if(child!=c->host)hideChild(child);
    RECT r{};GetClientRect(c->window,&r);SetWindowPos(c->host,HWND_TOP,0,0,r.right,r.bottom,SWP_NOACTIVATE|SWP_SHOWWINDOW);
    if(c->controller){c->controller->put_Bounds(r);c->controller->NotifyParentWindowPositionChanged();}
}
void fail(const Shared& c,HRESULT error){
    if(c->detached){return;}wchar_t message[256]{};wsprintfW(message,L"The Medicsoft PLMS installer interface could not start (0x%08X).",static_cast<unsigned int>(error));
    c->lastError=FAILED(error)?error:E_FAIL;
#ifndef PLMS_HOST_TEST
    MessageBoxW(c->window,message,L"Medicsoft PLMS Setup",MB_ICONERROR|MB_OK);
#else
    OutputDebugStringW(message);
#endif
    EnableWindow(GetDlgItem(c->window,IDCANCEL),TRUE);PostMessageW(c->window,WM_COMMAND,IDCANCEL,0);
}
std::vector<std::wstring> fields(const std::wstring& message){std::vector<std::wstring> values;size_t begin=0;for(;;){auto end=message.find(L'\t',begin);values.push_back(message.substr(begin,end==std::wstring::npos?end:end-begin));if(end==std::wstring::npos)break;begin=end+1;}return values;}
void browse(const Shared& c){
    ComPtr<IFileOpenDialog> picker;
    if(FAILED(CoCreateInstance(CLSID_FileOpenDialog,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(picker.put()))))return;
    FILEOPENDIALOGOPTIONS options{};picker->GetOptions(&options);picker->SetOptions(options|FOS_PICKFOLDERS|FOS_FORCEFILESYSTEM|FOS_PATHMUSTEXIST);
    picker->SetTitle(L"Choose Installation Folder");ComPtr<IShellItem> initial;
    if(SUCCEEDED(SHCreateItemFromParsingName(c->folder.c_str(),nullptr,IID_PPV_ARGS(initial.put()))))picker->SetFolder(initial.get());
    if(SUCCEEDED(picker->Show(c->window))){ComPtr<IShellItem> item;if(SUCCEEDED(picker->GetResult(item.put()))){LPWSTR path=nullptr;if(SUCCEEDED(item->GetDisplayName(SIGDN_FILESYSPATH,&path))){c->folder=path;CoTaskMemFree(path);SetWindowTextW(c->controls[1],c->folder.c_str());post(c,L"{\"kind\":\"folder\",\"folder\":"+json(c->folder)+L"}");}}}
}
void command(const Shared& c,const std::wstring& message){
    auto args=fields(message);if(args.empty()||c->detached)return;const auto& action=args[0];
    if(action==L"ready"){c->ready=true;if(c->hasState&&c->navigated)model(c);sync(c);return;}
    if(action==L"painted"){KillTimer(c->window,StartupTimer);bool first=!c->rendered;c->rendered=true;sync(c);if(first)ShowWindow(c->window,SW_SHOWNORMAL);if(c->controller&&!IsIconic(c->window)&&(first||GetForegroundWindow()==c->window))c->controller->MoveFocus(COREWEBVIEW2_MOVE_FOCUS_REASON_PROGRAMMATIC);return;}
    if(action==L"minimize"){ShowWindow(c->window,SW_MINIMIZE);return;}
    if(action==L"drag"){ReleaseCapture();PostMessageW(c->window,WM_NCLBUTTONDOWN,HTCAPTION,0);return;}
    if(action==L"browse"||action==L"install"){
        if(c->state!=0||args.size()!=4||args[1].empty()||args[1].size()>1000){post(c,L"{\"kind\":\"unlock\"}");return;}
        c->folder=args[1];c->desktop=args[2]==L"1";c->launch=args[3]==L"1";
        SetWindowTextW(c->controls[1],c->folder.c_str());setCheck(c->controls[2],c->desktop);setCheck(c->controls[3],c->launch);
        if(action==L"browse"){browse(c);return;}
        PostMessageW(c->window,WM_COMMAND,IDOK,0);
    }else if(action==L"continue"){
        if(c->state!=3||args.size()!=2||(!c->canRepair&&args[1]==L"repair"))return;
        if(args[1]!=L"repair"&&args[1]!=L"uninstall"&&args[1]!=L"exit")return;
        c->maintenance=args[1];setCheck(c->controls[4],args[1]==L"repair");setCheck(c->controls[5],args[1]==L"uninstall");setCheck(c->controls[6],args[1]==L"exit");
        PostMessageW(c->window,WM_COMMAND,IDOK,0);
    }else if(action==L"uninstall"){
        if(c->state!=4||args.size()!=2){return;}c->remove=args[1]==L"1";setCheck(c->controls[7],c->remove);PostMessageW(c->window,WM_COMMAND,IDOK,0);
    }else if(action==L"finish"){
        if(c->state!=2&&c->state!=6){return;}PostMessageW(c->window,WM_COMMAND,IDOK,0);
    }else if(action==L"cancel"&&c->state!=5){
        EnableWindow(GetDlgItem(c->window,IDCANCEL),TRUE);PostMessageW(c->window,WM_COMMAND,IDCANCEL,0);
    }
}
BOOL CALLBACK findProgress(HWND child,LPARAM ref){auto c=reinterpret_cast<Context*>(ref);wchar_t cls[64]{};GetClassNameW(child,cls,64);if(GetDlgCtrlID(child)==1004&&lstrcmpiW(cls,PROGRESS_CLASSW)==0)c->progress=child;return TRUE;}
void progress(const Shared& c){
    if(c->state!=1&&c->state!=5)return;
    if(!IsWindow(c->progress))EnumChildWindows(c->window,findProgress,reinterpret_cast<LPARAM>(c.get()));
    if(!IsWindow(c->progress))return;
    int position=static_cast<int>(SendMessageW(c->progress,PBM_GETPOS,0,0));int high=static_cast<int>(SendMessageW(c->progress,PBM_GETRANGE,FALSE,0));
    int value=high>0?std::max(0,std::min(100,static_cast<int>(100LL*position/high))):0;
    if(value!=c->percent){c->percent=value;post(c,L"{\"kind\":\"progress\",\"percent\":"+std::to_wstring(value)+L"}");}
}
LRESULT CALLBACK windowProc(HWND w,UINT m,WPARAM a,LPARAM l,UINT_PTR,DWORD_PTR ref){
    auto c=*reinterpret_cast<Shared*>(ref);
    if(m==SyncMessage){sync(c);return 0;}
    if(m==WM_TIMER&&a==StartupTimer){KillTimer(w,StartupTimer);if(!c->rendered)fail(c,HRESULT_FROM_WIN32(ERROR_TIMEOUT));return 0;}
    if(m==WM_TIMER&&a==SubclassId){progress(c);return 0;}
    if(m==WM_ERASEBKGND)return 1;
    if(m==WM_WINDOWPOSCHANGING&&!c->rendered){auto pos=reinterpret_cast<WINDOWPOS*>(l);if(pos->flags&SWP_SHOWWINDOW){pos->flags&=~SWP_SHOWWINDOW;pos->flags|=SWP_HIDEWINDOW;}}
    if(m==WM_PARENTNOTIFY&&LOWORD(a)==WM_CREATE){HWND child=reinterpret_cast<HWND>(l);if(GetParent(child)==w)hideChild(child);}
    if(m==WM_SIZE||m==WM_MOVE||m==WM_DPICHANGED||m==WM_PARENTNOTIFY)PostMessageW(w,SyncMessage,0,0);
    if(m==WM_NCDESTROY){c->detached=true;KillTimer(w,SubclassId);KillTimer(w,StartupTimer);if(c->controller)c->controller->Close();c->web.reset();c->controller.reset();c->environment.reset();RemoveWindowSubclass(w,windowProc,SubclassId);delete reinterpret_cast<Shared*>(ref);}
    return DefSubclassProc(w,m,a,l);
}
bool load(const std::wstring& folder){if(!loader)loader=LoadLibraryExW((folder+L"\\WebView2Loader.dll").c_str(),nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);return loader!=nullptr;}
void start(const Shared& c,const std::wstring& base){
    if(!load(base)){fail(c,HRESULT_FROM_WIN32(GetLastError()));return;}
    using Factory=HRESULT(STDAPICALLTYPE*)(PCWSTR,PCWSTR,ICoreWebView2EnvironmentOptions*,ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler*);
    auto factory=reinterpret_cast<Factory>(GetProcAddress(loader,"CreateCoreWebView2EnvironmentWithOptions"));if(!factory){fail(c,E_NOINTERFACE);return;}
    const auto html=readUtf8(base+L"\\plms-dialog.html");if(html.empty()){fail(c,HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND));return;}
    // NSIS owns and restricts its extraction directory. Browser data must
    // inherit normal per-user AppData permissions instead of that directory's ACL.
    PWSTR localAppData=nullptr;
    HRESULT profile=SHGetKnownFolderPath(FOLDERID_LocalAppData,KF_FLAG_CREATE,nullptr,&localAppData);
    if(FAILED(profile)){fail(c,profile);return;}
    c->userDataFolder=std::wstring(localAppData)+L"\\Medicsoft\\PLMS\\InstallerWebView"+(IsUserAnAdmin()?L"-Admin":L"-User");
    CoTaskMemFree(localAppData);
    int created=SHCreateDirectoryExW(nullptr,c->userDataFolder.c_str(),nullptr);
    if(created!=ERROR_SUCCESS&&created!=ERROR_ALREADY_EXISTS&&created!=ERROR_FILE_EXISTS){fail(c,HRESULT_FROM_WIN32(created));return;}
    DWORD attributes=GetFileAttributesW(c->userDataFolder.c_str());
    if(attributes==INVALID_FILE_ATTRIBUTES||!(attributes&FILE_ATTRIBUTE_DIRECTORY)){fail(c,HRESULT_FROM_WIN32(ERROR_DIRECTORY));return;}

    auto environmentHandler=new Callback<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler,HRESULT,ICoreWebView2Environment*>([c,html](HRESULT error,ICoreWebView2Environment* environment)->HRESULT{
        if(c->detached){return S_OK;}if(FAILED(error)||!environment){fail(c,error);return S_OK;}c->environment.reset(environment);
        auto controllerHandler=new Callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler,HRESULT,ICoreWebView2Controller*>([c,html](HRESULT result,ICoreWebView2Controller* controller)->HRESULT{
            if(c->detached){if(controller)controller->Close();return S_OK;}if(FAILED(result)||!controller){fail(c,result);return S_OK;}c->controller.reset(controller);controller->get_CoreWebView2(c->web.put());
            if(!c->web){fail(c,E_NOINTERFACE);return S_OK;}
            ComPtr<ICoreWebView2Settings> settings;c->web->get_Settings(settings.put());if(settings){settings->put_IsWebMessageEnabled(TRUE);settings->put_AreDefaultContextMenusEnabled(FALSE);settings->put_AreDevToolsEnabled(FALSE);settings->put_IsStatusBarEnabled(FALSE);}
            auto messageHandler=new Callback<ICoreWebView2WebMessageReceivedEventHandler,ICoreWebView2*,ICoreWebView2WebMessageReceivedEventArgs*>([c](ICoreWebView2*,ICoreWebView2WebMessageReceivedEventArgs* event)->HRESULT{
                LPWSTR source=nullptr;HRESULT hr=event->get_Source(&source);bool trusted=SUCCEEDED(hr)&&source&&lstrcmpW(source,L"about:blank")==0;CoTaskMemFree(source);if(!trusted)return S_OK;
                LPWSTR value=nullptr;if(SUCCEEDED(event->TryGetWebMessageAsString(&value))){if(value)command(c,value);CoTaskMemFree(value);}return S_OK;
            });
            EventRegistrationToken token{};c->web->add_WebMessageReceived(messageHandler,&token);messageHandler->Release();
            auto newWindowHandler=new Callback<ICoreWebView2NewWindowRequestedEventHandler,ICoreWebView2*,ICoreWebView2NewWindowRequestedEventArgs*>([](ICoreWebView2*,ICoreWebView2NewWindowRequestedEventArgs* event)->HRESULT{event->put_Handled(TRUE);return S_OK;});
            c->web->add_NewWindowRequested(newWindowHandler,&token);newWindowHandler->Release();
            // Inline JavaScript can announce ready before navigation has completed.
            // WebView2 can discard a host message sent during that navigation.
            auto completedHandler=new Callback<ICoreWebView2NavigationCompletedEventHandler,ICoreWebView2*,ICoreWebView2NavigationCompletedEventArgs*>([c](ICoreWebView2*,ICoreWebView2NavigationCompletedEventArgs* event)->HRESULT{
                if(c->navigated||c->detached)return S_OK;
                BOOL success=FALSE;event->get_IsSuccess(&success);
                if(!success){COREWEBVIEW2_WEB_ERROR_STATUS status{};event->get_WebErrorStatus(&status);
#ifdef PLMS_HOST_TEST
                    std::fprintf(stderr,"Initial HTML navigation failed: WebErrorStatus=%d\n",static_cast<int>(status));
#endif
                    fail(c,HRESULT_FROM_WIN32(ERROR_INVALID_DATA));return S_OK;}
                // NavigateToString is supplied by this host. Do not URL-filter its
                // initial internal load. Once loaded, this document never navigates.
                auto navigationLock=new Callback<ICoreWebView2NavigationStartingEventHandler,ICoreWebView2*,ICoreWebView2NavigationStartingEventArgs*>([c](ICoreWebView2*,ICoreWebView2NavigationStartingEventArgs* event)->HRESULT{++c->blockedNavigations;event->put_Cancel(TRUE);return S_OK;});
                EventRegistrationToken navigationToken{};c->web->add_NavigationStarting(navigationLock,&navigationToken);navigationLock->Release();
                c->navigated=true;if(c->ready&&c->hasState)model(c);return S_OK;
            });
            c->web->add_NavigationCompleted(completedHandler,&token);completedHandler->Release();
            sync(c);controller->put_IsVisible(TRUE);HRESULT navigate=c->web->NavigateToString(html.c_str());if(FAILED(navigate))fail(c,navigate);return S_OK;
        });
        HRESULT create=environment->CreateCoreWebView2Controller(c->host,controllerHandler);controllerHandler->Release();if(FAILED(create))fail(c,create);return S_OK;
    });
    HRESULT create=factory(nullptr,c->userDataFolder.c_str(),nullptr,environmentHandler);environmentHandler->Release();if(FAILED(create))fail(c,create);
}
}
extern "C" int __stdcall RuntimeAvailable(const wchar_t* base){if(!base||!load(base))return 0;using Version=HRESULT(STDAPICALLTYPE*)(PCWSTR,LPWSTR*);auto version=reinterpret_cast<Version>(GetProcAddress(loader,"GetAvailableCoreWebView2BrowserVersionString"));if(!version)return 0;LPWSTR value=nullptr;HRESULT result=version(nullptr,&value);int available=SUCCEEDED(result)&&value&&*value;CoTaskMemFree(value);return available;}
extern "C" void __stdcall Configure(HWND window,const wchar_t* brandPath){
    HMODULE self=nullptr;GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_PIN|GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,reinterpret_cast<LPCWSTR>(&Configure),&self);
    if(!IsWindow(window)||context(window)){return;}auto c=std::make_shared<Context>();c->window=window;
    HRESULT apartment=CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);if(FAILED(apartment)){fail(c,apartment);return;}c->comInitialized=true;
    auto holder=new Shared(c);if(!SetWindowSubclass(window,windowProc,SubclassId,reinterpret_cast<DWORD_PTR>(holder))){delete holder;return;}
    LONG_PTR style=GetWindowLongPtrW(window,GWL_STYLE);style&=~(WS_CAPTION|WS_THICKFRAME|WS_BORDER|WS_DLGFRAME);style|=WS_POPUP|WS_SYSMENU|WS_MINIMIZEBOX|WS_CLIPCHILDREN;SetWindowLongPtrW(window,GWL_STYLE,style);
    SetWindowLongPtrW(window,GWL_EXSTYLE,GetWindowLongPtrW(window,GWL_EXSTYLE)&~(WS_EX_DLGMODALFRAME|WS_EX_WINDOWEDGE|WS_EX_CLIENTEDGE|WS_EX_STATICEDGE));
    MONITORINFO info{};info.cbSize=sizeof(info);GetMonitorInfoW(MonitorFromWindow(window,MONITOR_DEFAULTTONEAREST),&info);
    double factor=std::min(static_cast<double>(GetDpiForWindow(window))/96.0,std::min((info.rcWork.right-info.rcWork.left-16)/952.0,(info.rcWork.bottom-info.rcWork.top-16)/998.0));
    int width=static_cast<int>(952*factor+0.5),height=static_cast<int>(998*factor+0.5);
    SetWindowPos(window,nullptr,info.rcWork.left+(info.rcWork.right-info.rcWork.left-width)/2,info.rcWork.top+(info.rcWork.bottom-info.rcWork.top-height)/2,width,height,SWP_NOZORDER|SWP_NOACTIVATE|SWP_FRAMECHANGED);
    HRGN region=CreateRoundRectRgn(0,0,width+1,height+1,static_cast<int>(18*factor),static_cast<int>(18*factor));if(!SetWindowRgn(window,region,FALSE))DeleteObject(region);
    c->host=CreateWindowExW(0,L"STATIC",L"",WS_CHILD|WS_VISIBLE|WS_CLIPCHILDREN,0,0,width,height,window,reinterpret_cast<HMENU>(HtmlHostId),GetModuleHandleW(nullptr),nullptr);
    SetTimer(window,StartupTimer,60000,nullptr);
    start(c,directory(brandPath?brandPath:L"."));
}
extern "C" int __stdcall Apply(HWND window,HWND,HWND,HWND,int){return IsWindow(window)?1:0;}
extern "C" void __stdcall BindPage(HWND window,HWND page){auto c=context(window);if(!c)return;c->page=page;for(auto& item:c->controls)item=nullptr;}
extern "C" void __stdcall BindOption(HWND window,int kind,HWND control){auto c=context(window);if(c&&kind>0&&kind<9)c->controls[kind]=control;}
extern "C" void __stdcall SetDataChoice(HWND window,int value){auto c=context(window);if(c)c->remove=value==1;}
extern "C" void __stdcall Layout(HWND window,int state){
    auto c=context(window);if(!c||state<0||state>6)return;KillTimer(window,SubclassId);c->hasState=true;c->state=state;c->percent=0;c->progress=nullptr;
    if(state==0){c->folder=text(c->controls[1]);c->desktop=checked(c->controls[2]);c->launch=checked(c->controls[3]);}
    if(state==3){c->canRepair=IsWindowEnabled(c->controls[4])!=FALSE;c->maintenance=checked(c->controls[6])?L"exit":checked(c->controls[5])?L"uninstall":L"repair";}
    if(state==4)c->remove=checked(c->controls[7]);
    if(state==1||state==5){EnumChildWindows(window,findProgress,reinterpret_cast<LPARAM>(c.get()));SetTimer(window,SubclassId,100,nullptr);}
    model(c);PostMessageW(window,SyncMessage,0,0);
}
extern "C" void __stdcall Detach(HWND window){auto c=context(window);if(!c)return;c->detached=true;KillTimer(window,SubclassId);KillTimer(window,StartupTimer);if(c->controller)c->controller->Close();c->web.reset();c->controller.reset();c->environment.reset();DWORD_PTR ref{};if(GetWindowSubclass(window,windowProc,SubclassId,&ref)){RemoveWindowSubclass(window,windowProc,SubclassId);delete reinterpret_cast<Shared*>(ref);}}

extern "C" void __stdcall Unlock(HWND window){auto c=context(window);if(c)post(c,L"{\"kind\":\"unlock\"}");}
