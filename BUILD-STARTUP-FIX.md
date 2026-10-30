# Windows HTML startup correction

The full log of job 121559163807 shows that the environment, controller and web
objects were created successfully. Navigation failed before the app loaded:
`navigation=0 ready=0 rendered=0`, document `about:blank`, no app and no images.
The prior timing patch alone did not resolve the failure.

The previous NavigationStarting handler rejected any navigation URI other than
about:blank. The host now allows its own initial NavigateToString call to load
without that URL comparison. Only after successful completion does it register
a navigation lock that cancels every subsequent navigation. New windows remain
blocked; CSP allows no external resources; native messages still require the
loaded about:blank document. This prevents the load guard from rejecting the
host-provided document while keeping the dialog locked to that document.

The navigation-completion handler distinguishes initial failure from subsequent
canceled navigation. Native smoke diagnostics now print WebErrorStatus as well
as controller/document stage information.

All mandatory native integration checks remain enabled. Local source and HTML
interaction checks pass. Windows compilation and runtime confirmation of this
revision require the next workflow run. Preview layout is unchanged.
