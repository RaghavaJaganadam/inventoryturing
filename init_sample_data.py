#!/usr/bin/env python3
"""
Initialize the database with sample equipment data
"""

from app import create_app, db
from app.models import Equipment, User, log_audit_event
from datetime import date, datetime
import json

def init_sample_data():
    app = create_app('development')
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if sample data already exists
        if Equipment.query.count() > 0:
            print("Sample data already exists. Skipping initialization.")
            return
        
        # Sample equipment data based on user requirements
        sample_equipment = [
            {
                "asset_tag": "EQ-1001",
                "name": "Xilinx FPGA Evaluation Board",
                "category": "FPGA Board",
                "model_number": "XC7A100T",
                "manufacturer": "Xilinx",
                "serial_number": "XIL-001",
                "procurement_date": "2023-01-10",
                "warranty_expiry": "2026-01-09",
                "status": "Available",
                "condition": "New",
                "chip_type": "FPGA",
                "package_type": "BGA",
                "pin_count": 256,
                "temperature_grade": "Industrial",
                "testing_status": "Untested",
                "revision_info": "Rev 1.0",
                "design_files": "https://gitlab.com/lab/fpga_board/design_files",
                "location": "Building 1 / Lab 2 / Shelf A",
                "assigned_to": None,
                "tags": "priority",
                "notes": "Initial stock",
                "purchase_cost": 2500.00
            },
            {
                "asset_tag": "EQ-1002",
                "name": "Intel Cyclone V Development Kit",
                "category": "FPGA Board",
                "model_number": "5CGXFC7C7F23C8N",
                "manufacturer": "Intel",
                "serial_number": "INT-002",
                "procurement_date": "2023-02-15",
                "warranty_expiry": "2026-02-14",
                "status": "Available",
                "condition": "Good",
                "chip_type": "FPGA",
                "package_type": "FBGA",
                "pin_count": 484,
                "temperature_grade": "Commercial",
                "testing_status": "Passed",
                "revision_info": "Rev 2.1",
                "design_files": "https://gitlab.com/lab/intel_dev_kit/files",
                "location": "Building 1 / Lab 2 / Shelf A",
                "assigned_to": None,
                "tags": "development, fpga",
                "notes": "Development kit with accessories",
                "purchase_cost": 1800.00
            },
            {
                "asset_tag": "EQ-1003",
                "name": "Keysight Oscilloscope",
                "category": "Test Equipment",
                "model_number": "DSOX3024T",
                "manufacturer": "Keysight",
                "serial_number": "KEY-003",
                "procurement_date": "2023-03-20",
                "warranty_expiry": "2026-03-19",
                "status": "In Use",
                "condition": "Good",
                "chip_type": None,
                "package_type": None,
                "pin_count": None,
                "temperature_grade": None,
                "testing_status": None,
                "revision_info": None,
                "design_files": None,
                "location": "Building 1 / Lab 3 / Bench 1",
                "assigned_to": None,  # Will be assigned to admin user
                "tags": "calibrated, precision",
                "notes": "200MHz, 4-channel digital oscilloscope",
                "purchase_cost": 5200.00
            },
            {
                "asset_tag": "EQ-1004",
                "name": "ARM Cortex-M4 MCU Sample",
                "category": "Chip Sample",
                "model_number": "STM32F407VGT6",
                "manufacturer": "STMicroelectronics",
                "serial_number": "STM-004",
                "procurement_date": "2023-04-10",
                "warranty_expiry": None,
                "status": "Available",
                "condition": "New",
                "chip_type": "ARM",
                "package_type": "LQFP",
                "pin_count": 100,
                "temperature_grade": "Industrial",
                "testing_status": "Untested",
                "revision_info": "Rev Y",
                "design_files": None,
                "location": "Building 1 / Lab 1 / Storage Cabinet",
                "assigned_to": None,
                "tags": "sample, cortex-m4",
                "notes": "High-performance MCU with FPU",
                "purchase_cost": 15.50
            },
            {
                "asset_tag": "EQ-1005",
                "name": "Logic Analyzer Pro",
                "category": "Logic Analyzer",
                "model_number": "LA2016",
                "manufacturer": "Kingst",
                "serial_number": "KNG-005",
                "procurement_date": "2023-05-15",
                "warranty_expiry": "2025-05-14",
                "status": "Under Maintenance",
                "condition": "Needs Repair",
                "chip_type": None,
                "package_type": None,
                "pin_count": None,
                "temperature_grade": None,
                "testing_status": None,
                "revision_info": None,
                "design_files": None,
                "location": "Building 1 / Maintenance Room",
                "assigned_to": None,
                "tags": "repair, logic-analyzer",
                "notes": "Channel 8 not working properly",
                "purchase_cost": 320.00
            },
            {
                "asset_tag": "EQ-1006",
                "name": "Power Supply Unit",
                "category": "Power Supply",
                "model_number": "E36313A",
                "manufacturer": "Keysight",
                "serial_number": "PWR-006",
                "procurement_date": "2023-06-01",
                "warranty_expiry": "2026-06-01",
                "status": "Available",
                "condition": "New",
                "chip_type": None,
                "package_type": None,
                "pin_count": None,
                "temperature_grade": None,
                "testing_status": None,
                "revision_info": None,
                "design_files": None,
                "location": "Building 1 / Lab 2 / Bench 2",
                "assigned_to": None,
                "tags": "power, bench",
                "notes": "Triple output, 6V/5A per channel",
                "purchase_cost": 890.00
            },
            {
                "asset_tag": "EQ-1007",
                "name": "ASIC Prototype Chip",
                "category": "Chip Sample",
                "model_number": "CUSTOM-V1",
                "manufacturer": "Custom Design",
                "serial_number": "CST-007",
                "procurement_date": "2023-07-20",
                "warranty_expiry": None,
                "status": "Available",
                "condition": "New",
                "chip_type": "ASIC",
                "package_type": "QFN",
                "pin_count": 64,
                "temperature_grade": "Commercial",
                "testing_status": "Failed",
                "revision_info": "Proto V1",
                "design_files": "https://gitlab.com/lab/asic_proto/v1",
                "location": "Building 1 / Lab 1 / Secure Storage",
                "assigned_to": None,
                "tags": "prototype, custom, failed",
                "notes": "First prototype - power issues identified",
                "purchase_cost": 5000.00
            },
            {
                "asset_tag": "EQ-1008",
                "name": "Arduino Uno Development Board",
                "category": "Development Board",
                "model_number": "A000066",
                "manufacturer": "Arduino",
                "serial_number": "ARD-008",
                "procurement_date": "2023-08-05",
                "warranty_expiry": "2024-08-04",
                "status": "Available",
                "condition": "Good",
                "chip_type": "Microcontroller",
                "package_type": "DIP",
                "pin_count": 28,
                "temperature_grade": "Commercial",
                "testing_status": "Passed",
                "revision_info": "Rev 3",
                "design_files": None,
                "location": "Building 1 / Lab 1 / Storage Drawer",
                "assigned_to": None,
                "tags": "arduino, prototyping",
                "notes": "Standard Arduino Uno R3",
                "purchase_cost": 25.00
            },
            {
                "asset_tag": "EQ-1009",
                "name": "Raspberry Pi 4 Model B",
                "category": "Development Board",
                "model_number": "RPI4-MODB-8GB",
                "manufacturer": "Raspberry Pi Foundation",
                "serial_number": "RPI-009",
                "procurement_date": "2023-09-10",
                "warranty_expiry": "2024-09-09",
                "status": "In Use",
                "condition": "Good",
                "chip_type": "ARM",
                "package_type": "BGA",
                "pin_count": 40,
                "temperature_grade": "Commercial",
                "testing_status": "Passed",
                "revision_info": "1.4",
                "design_files": None,
                "location": "Building 1 / Lab 3 / Workstation 1",
                "assigned_to": None,  # Will be assigned to admin user
                "tags": "raspberry-pi, linux",
                "notes": "8GB RAM model with heat sinks",
                "purchase_cost": 95.00
            },
            {
                "asset_tag": "EQ-1010",
                "name": "Function Generator",
                "category": "Test Equipment",
                "model_number": "33522B",
                "manufacturer": "Keysight",
                "serial_number": "FGN-010",
                "procurement_date": "2023-10-15",
                "warranty_expiry": "2026-10-14",
                "status": "Available",
                "condition": "New",
                "chip_type": None,
                "package_type": None,
                "pin_count": None,
                "temperature_grade": None,
                "testing_status": None,
                "revision_info": None,
                "design_files": None,
                "location": "Building 1 / Lab 2 / Bench 3",
                "assigned_to": None,
                "tags": "signal-generator, calibrated",
                "notes": "30 MHz arbitrary waveform generator",
                "purchase_cost": 2100.00
            }
        ]
        
        # Get admin user for assignments
        admin_user = User.query.filter_by(email='admin@lab.com').first()
        
        print("Adding sample equipment data...")
        
        for item_data in sample_equipment:
            equipment = Equipment()
            
            # Basic information
            equipment.asset_tag = item_data["asset_tag"]
            equipment.name = item_data["name"]
            equipment.category = item_data["category"]
            equipment.model_number = item_data.get("model_number")
            equipment.manufacturer = item_data.get("manufacturer")
            equipment.serial_number = item_data.get("serial_number")
            
            # Dates
            if item_data.get("procurement_date"):
                equipment.procurement_date = datetime.strptime(item_data["procurement_date"], '%Y-%m-%d').date()
            if item_data.get("warranty_expiry"):
                equipment.warranty_expiry = datetime.strptime(item_data["warranty_expiry"], '%Y-%m-%d').date()
            
            # Status and condition
            equipment.status = item_data["status"]
            equipment.condition = item_data["condition"]
            
            # Chip-specific fields
            equipment.chip_type = item_data.get("chip_type")
            equipment.package_type = item_data.get("package_type")
            equipment.pin_count = item_data.get("pin_count")
            equipment.temperature_grade = item_data.get("temperature_grade")
            equipment.testing_status = item_data.get("testing_status")
            equipment.revision_info = item_data.get("revision_info")
            
            # Files and location
            equipment.design_files = item_data.get("design_files")
            equipment.location = item_data["location"]
            
            # Assignment - assign some items to admin user
            if item_data["status"] == "In Use" and admin_user:
                equipment.assigned_to_id = admin_user.id
            
            # Cost and metadata
            equipment.purchase_cost = item_data.get("purchase_cost")
            equipment.current_value = item_data.get("purchase_cost")  # Default current value to purchase cost
            equipment.tags = item_data.get("tags")
            equipment.notes = item_data.get("notes")
            
            db.session.add(equipment)
            print(f"Added: {equipment.asset_tag} - {equipment.name}")
        
        try:
            db.session.commit()
            print(f"\nSuccessfully added {len(sample_equipment)} equipment items!")
            
            # Log the initialization
            if admin_user:
                log_audit_event(
                    admin_user.id,
                    'initialize_sample_data',
                    'equipment',
                    None,
                    None,
                    {'count': len(sample_equipment)}
                )
            
        except Exception as e:
            db.session.rollback()
            print(f"Error adding sample data: {str(e)}")
            return
        
        print("\nSample data initialization complete!")
        print("You can now log in with:")
        print("Email: admin@lab.com")
        print("Password: admin123")

# if __name__ == '__main__':
#     init_sample_data()

if __name__ == '__main__':
    confirm = input("WARNING: This will insert sample data. Type 'yes' to continue: ")
    if confirm.lower() == 'yes':
        init_sample_data()
    else:
        print("Cancelled.")
