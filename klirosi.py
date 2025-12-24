import random
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog

# -----------------------------
# Βασικό Παράθυρο
# -----------------------------
root = tk.Tk()
root.title("Επίσημη Κλήρωση με Διαστήματα Λαχνών")
root.geometry("700x600")

# Λίστες
laxnoi = []
dwra = []
nikites = []
dwra_shuffled = []

# -----------------------------
# Συναρτήσεις
# -----------------------------
def eisagogi_laxnon():
    global laxnoi
    laxnoi = []
    diastimata = []

    # Ζητάμε διαστήματα μέχρι να σταματήσει ο χρήστης
    while True:
        start = simpledialog.askinteger("Διάστημα Λαχνών", "Από αριθμό:", parent=root)
        end = simpledialog.askinteger("Διάστημα Λαχνών", "Έως αριθμό:", parent=root)
        if start is None or end is None:
            break
        if end < start:
            messagebox.showerror("Σφάλμα", "Το 'Έως' πρέπει να είναι μεγαλύτερο ή ίσο από το 'Από'.")
            continue
        diastimata.append((start, end))
        cont = messagebox.askyesno("Συνέχεια", "Θέλετε να προσθέσετε άλλο διάστημα;")
        if not cont:
            break

    # Δημιουργία λίστας διαθέσιμων λαχνών
    for s, e in diastimata:
        laxnoi.extend(range(s, e + 1))
    
    # Εμφάνιση διαστημάτων και συνολικών λαχνών στο παράθυρο
    text_results.delete("1.0", tk.END)
    text_results.insert(tk.END, "--- Διαθέσιμα Διαστήματα Λαχνών ---\n")
    for s, e in diastimata:
        text_results.insert(tk.END, f"{s} - {e}\n")
    text_results.insert(tk.END, f"\nΣυνολικοί διαθέσιμοι λαχνοί: {len(laxnoi)}\n")
    messagebox.showinfo("ΟΚ", f"Συνολικοί διαθέσιμοι λαχνοί: {len(laxnoi)}")

def eisagogi_doron():
    global dwra
    dwra = []
    choice = messagebox.askyesno("Επιλογή", "Θέλετε να φορτώσετε τα δώρα από αρχείο txt;")
    if choice:
        filename = filedialog.askopenfilename(title="Επιλέξτε αρχείο δώρων", filetypes=[("Text Files","*.txt")])
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                dwra = [line.strip() for line in f if line.strip()]
            messagebox.showinfo("ΟΚ", f"Φορτώθηκαν {len(dwra)} δώρα από το αρχείο.")
    else:
        total = simpledialog.askinteger("Δώρα", "Πόσα δώρα υπάρχουν;", parent=root)
        if total is None or total <= 0:
            return
        for i in range(total):
            gift = simpledialog.askstring("Δώρο", f"Δώρο {i+1}:")
            if gift:
                dwra.append(gift)
    messagebox.showinfo("ΟΚ", f"Έτοιμη η λίστα με {len(dwra)} δώρα.")

def klirwsi():
    global nikites, dwra_shuffled
    if not laxnoi or not dwra:
        messagebox.showwarning("Σφάλμα", "Πρέπει πρώτα να εισάγετε λαχνούς και δώρα!")
        return
    if len(dwra) > len(laxnoi):
        messagebox.showerror("Σφάλμα", "Τα δώρα είναι περισσότερα από τους διαθέσιμους λαχνούς!")
        return
    
    # Seed για επίσημη κλήρωση
    seed_input = simpledialog.askstring("Seed", "Δώστε έναν αριθμό seed για επίσημη κλήρωση:", parent=root)
    if seed_input:
        random.seed(seed_input)
    
    nikites = random.sample(laxnoi, len(dwra))
    dwra_shuffled = dwra.copy()
    random.shuffle(dwra_shuffled)
    
    # Καθαρισμός προηγούμενων αποτελεσμάτων (εκτός από τα διαστήματα)
    text_results.insert(tk.END, "\n--- ΑΠΟΤΕΛΕΣΜΑΤΑ ΚΛΗΡΩΣΗΣ ---\n")
    
    # Εμφάνιση νικητών στο ίδιο παράθυρο
    for laxnos, gift in zip(nikites, dwra_shuffled):
        entry = f"Λαχνός {laxnos} κερδίζει: {gift}\n"
        text_results.insert(tk.END, entry)
    
    # Αποθήκευση σε αρχείο
    with open("apotelesmata_klirwsis.txt", "w", encoding="utf-8") as f:
        for laxnos, gift in zip(nikites, dwra_shuffled):
            f.write(f"Λαχνός {laxnos} κερδίζει: {gift}\n")
    messagebox.showinfo("Τέλος", "Η κλήρωση ολοκληρώθηκε και αποθηκεύτηκε σε apotelesmata_klirwsis.txt")

# -----------------------------
# Κουμπιά
# -----------------------------
btn1 = tk.Button(root, text="Εισαγωγή Διαστημάτων Λαχνών", width=35, command=eisagogi_laxnon)
btn1.pack(pady=10)

btn2 = tk.Button(root, text="Εισαγωγή Δώρων", width=35, command=eisagogi_doron)
btn2.pack(pady=10)

btn3 = tk.Button(root, text="Κλήρωση", width=35, command=klirwsi)
btn3.pack(pady=10)

# -----------------------------
# Περιοχή εμφάνισης αποτελεσμάτων
# -----------------------------
text_results = tk.Text(root, height=25, width=90)
text_results.pack(pady=20)

root.mainloop()
