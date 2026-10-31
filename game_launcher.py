import tkinter as tk

root = tk.Tk()
root.title("Nexa Game Runtime")
root.geometry("800x600")
root.configure(bg="black")

label = tk.Label(
    root,
    text="Nexa Game Runtime",
    fg="white",
    bg="black",
    font=("Arial", 28)
)
label.pack(expand=True)

root.mainloop()
