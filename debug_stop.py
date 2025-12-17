import main
root = main.create_ui()
app = main._app_instance
btn = app.stop_button
print('stop_button_exists', btn is not None)
print('visible?', btn.winfo_ismapped())
print('state:', btn.cget('state'))
print('text:', btn.cget('text'))
print('width,height:', btn.winfo_width(), btn.winfo_height())
# Print parent children
print('parent children:', [child for child in btn.master.winfo_children()])
root.destroy()