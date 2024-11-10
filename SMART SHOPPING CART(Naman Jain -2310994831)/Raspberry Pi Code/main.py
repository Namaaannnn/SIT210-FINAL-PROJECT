import tkinter as tk
from tkinter import messagebox, font, Toplevel
from datetime import datetime
import json
import qrcode
import paho.mqtt.client as mqtt 
from PIL import Image, ImageTk  

class BillApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Cart")
        self.root.geometry("800x480")

        # Define color theme for dark mode
        self.bg_color = "#2e2e2e"  # Dark gray background
        self.fg_color = "white"     # White text
        self.entry_bg = "#444444"   # Darker gray for entry fields
        self.button_bg = "#555555"  # Medium gray for buttons
        self.table_header_bg = "#3e3e3e"  # Darker gray for table headers
        self.table_row1_bg = "#3e3e3e"     # Darker gray for table rows
        self.table_row2_bg = "#2e2e2e"     # Dark gray for alternating rows

        # Apply the background color to the main window
        self.root.configure(bg=self.bg_color)

        # Define font variables
        self.heading_font = ("Arial", 10, "bold")
        self.normal_font = ("Arial", 8, "bold")
        self.button_font = ("Arial", 8, "bold")

        # Main Heading Label
        tk.Label(root, text="Welcome to Smart Cart", font=self.heading_font, bg=self.bg_color, fg=self.fg_color, padx=20).grid(row=0, column=0, columnspan=2, pady=10)

        # Create and place labels and entries with appropriate colors
        tk.Label(root, text="Name :", font=self.normal_font, anchor='w', bg=self.bg_color, fg=self.fg_color).grid(row=1, column=0, padx=10, pady=10, sticky='w')
        tk.Label(root, text="Contact :", font=self.normal_font, anchor='w', bg=self.bg_color, fg=self.fg_color).grid(row=2, column=0, padx=10, pady=10, sticky='w')

        self.name_entry = tk.Entry(root, width=30, font=self.normal_font, bg=self.entry_bg, fg=self.fg_color, insertbackground=self.fg_color)
        
        # Only allow numeric input in contact entry field
        validate_command = root.register(self.validate_contact)
        self.contact_entry = tk.Entry(root, width=30, font=self.normal_font, bg=self.entry_bg, fg=self.fg_color, insertbackground=self.fg_color, validate="key", validatecommand=(validate_command, "%P"))
        
        self.name_entry.grid(row=1, column=1, padx=10, pady=10)
        self.contact_entry.grid(row=2, column=1, padx=10, pady=10)

        # Create and place submit button with appropriate colors
        submit_button = tk.Button(root, text="Submit", font=self.button_font, bg=self.button_bg, fg=self.fg_color, command=self.submit)
        submit_button.grid(row=3, column=0, columnspan=2, pady=10)

        # On-screen keyboard container
        self.keyboard_frame = tk.Frame(root, bg=self.bg_color)
        self.keyboard_frame.grid(row=4, column=0, columnspan=2, pady=10)

        self.create_keyboard()

    def create_keyboard(self):
        """Creates an on-screen keyboard"""
        keys = [
            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
            'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P',
            'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L',
            'Z', 'X', 'C', 'V', 'B', 'N', 'M', 'Back', 'Space', 'Enter'
        ]
        
        row = 0
        col = 0
        for key in keys:
            button = tk.Button(self.keyboard_frame, text=key, font=self.normal_font, bg=self.button_bg, fg="white", width=5, height=2, command=lambda key=key: self.on_key_press(key))
            button.grid(row=row, column=col, padx=5, pady=5)
            col += 1
            if col == 10:
                col = 0
                row += 1

    def on_key_press(self, key):

        current_focus = self.root.focus_get()
        
        if key == 'Back':
            if current_focus == self.name_entry:
                current_text = self.name_entry.get()
                if len(current_text) > 0:  # Ensure there's something to delete
                    self.name_entry.delete(len(current_text)-1, tk.END)
            elif current_focus == self.contact_entry:
                current_text = self.contact_entry.get()
                if len(current_text) > 0:  # Ensure there's something to delete
                    self.contact_entry.delete(len(current_text)-1, tk.END)

        elif key == 'Space':
            if current_focus == self.name_entry:
                self.name_entry.insert(tk.END, ' ')
            elif current_focus == self.contact_entry:
                self.contact_entry.insert(tk.END, ' ')
                
        elif key == 'Enter':
            self.submit()
            
        else:
            # Insert key for any other character (letter/number)
            if current_focus == self.name_entry:
                self.name_entry.insert(tk.END, key)
            elif current_focus == self.contact_entry:
                self.contact_entry.insert(tk.END, key)


    def setup_mqtt(self):
        # MQTT connection parameters
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        # Connect to the MQTT broker
        self.mqtt_client.connect("broker.emqx.io", 1883, 60)
        self.mqtt_client.loop_start()  # Start MQTT loop in a separate thread

    def process_mqtt_data(self, mqtt_data):
        operation = mqtt_data.split(',')[0]
        item = mqtt_data.split(',')[1]

        if operation == "-" and item != "Inventory":
            self.remove_item(item)
        elif operation == "+" and item != "Inventory":
            self.add_item(item)
        elif operation == "+" and item == "Inventory":
            self.update_inventory()  # Call the update_inventory function
            messagebox.showinfo("Inventory Updated", "Inventory updated all item's quantity is increased by 10")

    def remove_item(self, item):
        # Load the bill data
        try:
            with open("bill.json", "r") as file:
                bill_data = json.load(file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load bill data: {e}")
            return

        # Load the inventory data
        try:
            with open("inventory.json", "r") as inv_file:
                inventory_data = json.load(inv_file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load inventory data: {e}")
            return

        # Find the item in the bill
        bill_item = next((bill_item for bill_item in bill_data if bill_item["item_name"].lower() == item.lower()), None)
        if not bill_item:
            messagebox.showwarning("Item Not Found", f"The item '{item}' is not in the bill.")
            return

        # Decrement the quantity of the item in the bill
        bill_item["quantity"] = max(0, bill_item["quantity"] - 1)
        if bill_item["quantity"] == 0:
            bill_data.remove(bill_item)  # Remove the item if quantity reaches zero

        # Find the item in the inventory and increase the quantity by 1
        inventory_item = next((inv_item for inv_item in inventory_data if inv_item["item_name"].lower() == item.lower()), None)
        if inventory_item:
            inventory_item["quantity"] += 1

        # Save the updated bill data back to the JSON file
        with open("bill.json", "w") as file:
            json.dump(bill_data, file, indent=4)

        # Save the updated inventory data back to the JSON file
        with open("inventory.json", "w") as inv_file:
            json.dump(inventory_data, inv_file, indent=4)

        print(f"Item '{item}' removed or updated successfully in bill data and inventory updated.")


    import json

    def add_item(self, item_name):
        # Load inventory data to fetch item details
        try:
            with open("inventory.json", "r") as inv_file:
                inventory_data = json.load(inv_file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load inventory data: {e}")
            return
        
        # Find item in inventory
        item_details = next((item for item in inventory_data if item["item_name"].lower() == item_name.lower()), None)
        if not item_details:
            messagebox.showwarning("Item Not Found", f"The item '{item_name}' is not available in inventory.")
            return

        # Check if there is enough quantity in inventory
        if item_details["quantity"] <= 0:
            messagebox.showwarning("Out of Stock", f"The item '{item_name}' is out of stock.")
            return
        
        # Load the current bill data
        try:
            with open("bill.json", "r") as bill_file:
                bill_data = json.load(bill_file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load bill data: {e}")
            return

        # Check if the item is already in the bill
        bill_item = next((item for item in bill_data if item["item_name"].lower() == item_name.lower()), None)
        
        if bill_item:
            # If item is already in bill, increase the quantity by 1
            bill_item["quantity"] += 1
        else:
            # If item is not in the bill, add it with quantity 1
            new_item = {
                "item_code": item_details["item_code"],
                "item_name": item_details["item_name"],
                "cost_per_unit": item_details["price_per_quantity"],
                "quantity": 1
            }
            bill_data.append(new_item)
        
        # Decrease inventory quantity by 1
        item_details["quantity"] -= 1

        # Save the updated bill data back to the JSON file
        with open("bill.json", "w") as bill_file:
            json.dump(bill_data, bill_file, indent=4)

        # Save the updated inventory data back to the JSON file
        with open("inventory.json", "w") as inv_file:
            json.dump(inventory_data, inv_file, indent=4)

        print(f"Item '{item_name}' added or updated successfully in bill data and inventory updated.")

        # Update the details window with the latest bill data if it's open
        if hasattr(self, "details_window") and self.details_window.winfo_exists():
            self.display_bill_data(self.details_window, self.name_entry.get(), self.contact_entry.get())


    def update_inventory(self):
        try:
            # Load inventory data from inventory.json
            with open("inventory.json", "r") as file:
                inventory_data = json.load(file)

            # Increment each item's quantity by 10
            for item in inventory_data:
                item["quantity"] += 10

            # Save the updated inventory back to inventory.json
            with open("inventory.json", "w") as file:
                json.dump(inventory_data, file, indent=4)
            
            print("Inventory updated: all item quantities increased by 10")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to update inventory: {e}")
            
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT broker")
            # Subscribe to the topic
            client.subscribe("RF_SMART_CART_DTS")
        else:
            print("Failed to connect, return code:", rc)

    def on_message(self, client, userdata, msg):
        try:
            # Decode and parse the JSON message
            raw_payload = msg.payload.decode().strip()
            print("Received MQTT message:", raw_payload)
            self.process_mqtt_data(raw_payload)
        except json.JSONDecodeError:
            print("Failed to decode message")
    
    def validate_contact(self, new_value):
        # Allow only digits and restrict any non-numeric input
        return new_value.isdigit() or new_value == ""

    def submit(self):
        # Get data from entries
        name = self.name_entry.get().strip()
        contact = self.contact_entry.get().strip()

        # Validate data
        if name == "" or contact == "":
            messagebox.showwarning("Input Error", "Please fill in all fields.")
            return
        
        if len(contact) < 10:
            messagebox.showwarning("Contact Error", "Please enter a 10-digit contact number.")
            return

        # Open a new window with the details
        self.open_details_window(name, contact)
        self.clear_entries()

    def open_details_window(self, name, contact):
        # Initialize MQTT client and connect to the broker
        self.setup_mqtt()

        # Get current date and time
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create new Toplevel window
        details_window = Toplevel(self.root)
        details_window.title("Billing System")
        details_window.configure(bg=self.bg_color)

        # Display the details with appropriate colors
        tk.Label(details_window, text=f"Name: {name}", font=self.normal_font, anchor="w", bg=self.bg_color, fg=self.fg_color).grid(row=0, column=0, pady=2, padx=20, sticky="w")
        tk.Label(details_window, text=f"Contact: {contact}", font=self.normal_font, anchor="w", bg=self.bg_color, fg=self.fg_color).grid(row=0, column=4, pady=2, padx=20, sticky="w")
        tk.Label(details_window, text=f"Date and Time: {current_datetime}", font=self.normal_font, anchor="w", bg=self.bg_color, fg=self.fg_color).grid(row=1, column=0, columnspan=3, pady=5, padx=20, sticky="w")
        tk.Button(details_window, text="View Inventory", padx=10, pady=5, font=self.normal_font, bg=self.button_bg, fg=self.fg_color, command=self.view_inventory).grid(row=1, column=4, padx=20, pady=5, sticky="w")

        # Pass name and contact to display_bill_data
        self.display_bill_data(details_window, name, contact, current_datetime)

        # Set up periodic update of bill data every 1000 milliseconds
        self.update_bill_data(details_window,current_datetime, name, contact)

    def display_bill_data(self, details_window, name, contact, current_datetime):
        # Clear existing widgets to prevent duplicate entries and buttons
        for widget in details_window.grid_slaves():
            widget.grid_forget()  # Remove all widgets in details_window

        # Reload bill data from the JSON file
        try:
            with open("bill.json", "r") as file:
                bill_data = json.load(file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load bill data: {e}")
            return

        # Display the details with appropriate colors
        tk.Label(details_window, text=f"Name: {name}", font=self.normal_font, anchor="w", bg=self.bg_color, fg=self.fg_color).grid(row=0, column=0, pady=5, padx=20, sticky="w")
        tk.Label(details_window, text=f"Contact: {contact}", font=self.normal_font, anchor="w", bg=self.bg_color, fg=self.fg_color).grid(row=0, column=4, pady=5, padx=20, sticky="w")
        tk.Label(details_window, text=f"Date and Time: {current_datetime}", font=self.normal_font, anchor="w", bg=self.bg_color, fg=self.fg_color).grid(row=1, column=0, columnspan=3, pady=5, padx=20, sticky="w")
        tk.Button(details_window, text="View Inventory", padx=10, pady=5, font=self.normal_font, bg=self.button_bg, fg=self.fg_color, command=self.view_inventory).grid(row=1, column=4, padx=20, pady=5, sticky="w")

        # Add table headers
        tk.Label(details_window, text="Item Code", font=self.normal_font, width=15, anchor='w', bg=self.table_header_bg, fg=self.fg_color).grid(row=2, column=0, padx=10, pady=10, sticky='w')
        tk.Label(details_window, text="Item Name", font=self.normal_font, width=20, anchor='w', bg=self.table_header_bg, fg=self.fg_color).grid(row=2, column=1, padx=10, pady=10, sticky='w')
        tk.Label(details_window, text="Quantity", font=self.normal_font, width=20, anchor='w', bg=self.table_header_bg, fg=self.fg_color).grid(row=2, column=2, padx=10, pady=10, sticky='w')
        tk.Label(details_window, text="Price per Unit", font=self.normal_font, width=20, anchor='w', bg=self.table_header_bg, fg=self.fg_color).grid(row=2, column=3, padx=10, pady=10, sticky='w')
        tk.Label(details_window, text="Total Price", font=self.normal_font, width=20, anchor='w', bg=self.table_header_bg, fg=self.fg_color).grid(row=2, column=4, padx=10, pady=10, sticky='w')

        # Initialize total sum
        total_sum = 0
        row = 4  # Start from the fourth row

        # Display non-zero quantity items in the bill
        for item in bill_data:
            if item['quantity'] > 0:  # Only display items with quantity > 0
                total_price = item["quantity"] * item["cost_per_unit"]
                total_sum += total_price

                row_color = self.table_row1_bg if (row - 4) % 2 == 0 else self.table_row2_bg
                tk.Label(details_window, text=item["item_code"], font=self.normal_font, width=15, bg=row_color, fg=self.fg_color, relief="solid", padx=10, pady=5, anchor='w').grid(row=row, column=0, padx=1, pady=1, sticky='w')
                tk.Label(details_window, text=item["item_name"], font=self.normal_font, width=20, bg=row_color, fg=self.fg_color, relief="solid", padx=10, pady=5, anchor='w').grid(row=row, column=1, padx=1, pady=1, sticky='w')
                tk.Label(details_window, text=f"{item['quantity']}", font=self.normal_font, width=15, bg=row_color, fg=self.fg_color, relief="solid", padx=10, pady=5, anchor='w').grid(row=row, column=2, padx=1, pady=1, sticky='w')
                tk.Label(details_window, text=f"₹ {item['cost_per_unit']:.2f}", font=self.normal_font, width=20, bg=row_color, fg=self.fg_color, relief="solid", padx=10, pady=5, anchor='w').grid(row=row, column=3, padx=1, pady=1, sticky='w')
                tk.Label(details_window, text=f"₹ {total_price:.2f}", font=self.normal_font, width=20, bg=row_color, fg=self.fg_color, relief="solid", padx=10, pady=5, anchor='w').grid(row=row, column=4, padx=1, pady=1, sticky='w')
                row += 1

        # Display total sum and add the "Checkout" button once at the end
        tk.Label(details_window, text="Total Sum:", font=self.normal_font, width=20, anchor='e', bg=self.bg_color, fg=self.fg_color).grid(row=row, column=3, padx=10, pady=5, sticky="e")
        tk.Label(details_window, text=f"₹ {total_sum:.2f}", font=self.normal_font, width=20, anchor='w', bg=self.bg_color, fg=self.fg_color).grid(row=row, column=4, padx=10, pady=5, sticky="w")

        # Place "Checkout" button below the total sum
        tk.Button(details_window, text="Checkout", bg=self.button_bg, fg=self.fg_color, font=self.normal_font, command=lambda: self.show_qr_code(name, contact, total_sum)).grid(row=row + 1, column=0, columnspan=5, pady=5)

    def update_bill_data(self, details_window, current_datetime, name, contact):
        # This function is called every 1000ms to update bill data in the details window
        self.display_bill_data(details_window, name, contact, current_datetime)
        details_window.after(2000, self.update_bill_data, details_window, current_datetime, name, contact)

    def clear_entries(self):
        # Clear entries after submission
        self.name_entry.delete(0, tk.END)
        self.contact_entry.delete(0, tk.END)

    def load_inventory(self):
        # Load inventory from the JSON file
        try:
            with open("inventory.json", "r") as file:
                inventory = json.load(file)
            return inventory
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load inventory: {e}")
            return []

    def view_inventory(self):
        # Create new Toplevel window for inventory
        inventory_window = Toplevel(self.root)
        inventory_window.title("Inventory List")
        inventory_window.configure(bg=self.bg_color)

        # Load inventory data
        inventory = self.load_inventory()

        if not inventory:
            messagebox.showwarning("No Inventory", "No inventory data available.")
            return

        # Create table headers with appropriate colors
        tk.Label(inventory_window, text="Item Code", font=self.normal_font, width=15, anchor='w', bg=self.table_header_bg, fg=self.fg_color).grid(row=0, column=0, padx=10, pady=10, sticky='w')
        tk.Label(inventory_window, text="Item Name", font=self.normal_font, width=20, anchor='w', bg=self.table_header_bg, fg=self.fg_color).grid(row=0, column=1, padx=10, pady=10, sticky='w')
        tk.Label(inventory_window, text="Quantity", font=self.normal_font, width=20, anchor='w', bg=self.table_header_bg, fg=self.fg_color).grid(row=0, column=2, padx=10, pady=10, sticky='w')
        tk.Label(inventory_window, text="Price per Quantity", font=self.normal_font, width=20, anchor='w', bg=self.table_header_bg, fg=self.fg_color).grid(row=0, column=3, padx=10, pady=10, sticky='w')


        # Display inventory items in table format
        for i, item in enumerate(inventory, 1):
            # Row color alternation for better visibility
            row_color = self.table_row1_bg if i % 2 == 0 else self.table_row2_bg
            
            # Create labels with padding and styling
            tk.Label(inventory_window, text=item["item_code"], font=self.normal_font, width=15, bg=row_color, fg=self.fg_color, relief="solid", padx=10, pady=5, anchor='w').grid(row=i, column=0, padx=1, pady=1, sticky='w')
            tk.Label(inventory_window, text=item["item_name"], font=self.normal_font, width=20, bg=row_color, fg=self.fg_color, relief="solid", padx=10, pady=5, anchor='w').grid(row=i, column=1, padx=1, pady=1, sticky='w')
            tk.Label(inventory_window, text=f"{item['quantity']}", font=self.normal_font, width=15, bg=row_color, fg=self.fg_color, relief="solid", padx=10, pady=5, anchor='w').grid(row=i, column=2, padx=1, pady=1, sticky='w')
            tk.Label(inventory_window, text=f"₹ {item['price_per_quantity']:.2f}", font=self.normal_font, width=20, bg=row_color, fg=self.fg_color, relief="solid", padx=10, pady=5, anchor='w').grid(row=i, column=3, padx=1, pady=1, sticky='w')
    
    def show_qr_code(self, name, contact, total_sum):
        # Create a new Toplevel window for QR code
        qr_window = Toplevel(self.root)
        qr_window.title("QR Code")
        qr_window.configure(bg=self.bg_color)

        # Data to encode in the QR code
        data = f"Name: {name}\nContact: {contact}\nTotal: ₹ {total_sum:.2f}"

        # Generate QR code and save it temporarily
        qr = qrcode.make(data)
        qr.save("temp_qr.png")  # Save the QR code as an image file

        # Open the saved image with PIL and convert to ImageTk.PhotoImage for Tkinter compatibility
        qr_image = Image.open("temp_qr.png")
        qr_photo = ImageTk.PhotoImage(qr_image)

        # Display the QR code in the new window
        tk.Label(qr_window, image=qr_photo, bg=self.bg_color).pack(pady=20)

        # Keep a reference to prevent garbage collection
        qr_window.qr_photo = qr_photo  # Prevents the image from being garbage collected

# Create the main application window and run the app
if __name__ == "__main__":
    with open('bill.json', 'w') as file:
        json.dump([], file)
    root = tk.Tk()
    app = BillApp(root)
    root.mainloop()