import pyautogui
import time
import threading
import sys

class SimpleAutoClicker:
    def __init__(self, interval=5.0):
        self.interval = interval
        self.running = False
        self.thread = None
        self.click_position = None
    
    def set_click_position(self):
        """Ορίζει τη θέση κλικ"""
        print("Μετακίνησε το ποντίκι στη θέση που θες και πάτα ENTER...")
        input()  # Αναμονή για Enter
        x, y = pyautogui.position()
        self.click_position = (x, y)
        print(f"✓ Θέση κλικ ορίστηκε: ({x}, {y})")
        return (x, y)
    
    def show_current_position(self):
        """Δείχνει την τρέχουσα θέση"""
        x, y = pyautogui.position()
        print(f"Τρέχουσα θέση ποντικιού: ({x}, {y})")
    
    def click_loop(self):
        """Βρόχος αυτόματου κλικ"""
        click_count = 0
        while self.running:
            try:
                if self.click_position:
                    x, y = self.click_position
                    pyautogui.click(x, y)
                    print(f"Κλικ #{click_count+1} στη θέση ({x}, {y}) - {time.strftime('%H:%M:%S')}")
                else:
                    pyautogui.click()
                    print(f"Κλικ #{click_count+1} στην τρέχουσα θέση - {time.strftime('%H:%M:%S')}")
                
                click_count += 1
                time.sleep(self.interval)
            except Exception as e:
                print(f"Σφάλμα: {e}")
                break
    
    def start(self):
        """Ξεκινάει το αυτόματο κλικ"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.click_loop)
            self.thread.daemon = True
            self.thread.start()
            print(f"▶️ Αυτόματο κλικ ξεκίνησε (διάστημα: {self.interval} δευτερόλεπτα)")
            print("   Πατήστε Ctrl+C για να σταματήσετε")
    
    def stop(self):
        """Σταματάει το αυτόματο κλικ"""
        self.running = False
        print("⏹️ Αυτόματο κλικ σταμάτησε")

def print_menu():
    print("\n" + "="*50)
    print("         AUTO CLICKER - ΟΔΗΓΙΕΣ")
    print("="*50)
    print("1 - Ορισμός νέας θέσης κλικ")
    print("2 - Εμφάνιση τρέχουσας θέσης ποντικιού")
    print("3 - Έναρξη αυτόματου κλικ")
    print("4 - Παύση αυτόματου κλικ")
    print("5 - Αλλαγή διαστήματος κλικ")
    print("0 - Έξοδος")
    print("="*50)

def main():
    print("🚀 Auto Clicker για Windows")
    print("Δημιουργήθηκε για χρήση χωρίς εγκατάσταση Python")
    
    clicker = SimpleAutoClicker(interval=5.0)
    
    try:
        while True:
            print_menu()
            choice = input("Επιλογή: ").strip()
            
            if choice == "1":
                clicker.set_click_position()
            
            elif choice == "2":
                clicker.show_current_position()
            
            elif choice == "3":
                if clicker.click_position:
                    print(f"Θα γίνει κλικ στη θέση: {clicker.click_position}")
                else:
                    print("Θα γίνει κλικ στην τρέχουσα θέση του ποντικιού")
                
                confirm = input("Είστε έτοιμοι; (y/n): ")
                if confirm.lower() == 'y':
                    clicker.start()
                else:
                    print("Ακυρώθηκε")
            
            elif choice == "4":
                clicker.stop()
            
            elif choice == "5":
                try:
                    new_interval = float(input("Νέο διάστημα (δευτερόλεπτα): "))
                    clicker.interval = new_interval
                    print(f"Διάστημα ορίστηκε: {new_interval} δευτερόλεπτα")
                except ValueError:
                    print("Μη έγκυρη τιμή!")
            
            elif choice == "0":
                clicker.stop()
                print("👋 Έξοδος από το πρόγραμμα")
                break
            
            else:
                print("Μη έγκυρη επιλογή!")
            
            print("\n" + "-"*30)
    
    except KeyboardInterrupt:
        clicker.stop()
        print("\n\nΠρόγραμμα τερματίστηκε")

if __name__ == "__main__":
    main()