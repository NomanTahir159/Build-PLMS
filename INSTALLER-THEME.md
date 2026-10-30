# Medicsoft PLMS installer appearance

The approved HTML/CSS is now the actual installer/uninstaller renderer, hosted
in Microsoft WebView2. The old GDI approximation has been replaced.

See [APPROVED-DIALOG-IMPLEMENTATION.md](APPROVED-DIALOG-IMPLEMENTATION.md) for the
source, all seven states, runtime preparation, progress/cancellation behavior,
and validation limits. Windows visual confirmation remains pending.
