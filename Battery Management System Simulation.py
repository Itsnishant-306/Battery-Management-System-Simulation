# Battery Management System Simulation


import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import time
from datetime import datetime
import os

class BatteryCell:
    """Simulation of an individual battery cell with realistic parameters"""
    
    def __init__(self, capacity=3200, internal_resistance=0.02, 
                 max_voltage=4.2, min_voltage=2.8, 
                 current_rating=10, cycle_count=0):
        """Initialize a battery cell with default parameters for a Li-ion cell"""
        self.capacity = capacity  # in mAh
        self.internal_resistance = internal_resistance  # in ohms
        self.max_voltage = max_voltage  # in volts
        self.min_voltage = min_voltage  # in volts
        self.current_rating = current_rating  # in amperes
        self.cycle_count = cycle_count  # number of charge/discharge cycles
        
        # State variables
        self.current_voltage = max_voltage  # start fully charged
        self.state_of_charge = 100  # percentage
        self.temperature = 25  # degrees Celsius
        self.current_flow = 0  # amperes (positive for charging, negative for discharging)
        self.health = 100  # percentage
        
        # Thermal properties
        self.thermal_resistance = 10  # K/W
        self.heat_capacity = 200  # J/K
        
        # Random variations to simulate real-world differences
        self.capacity *= (1 + np.random.normal(0, 0.03))  # 3% variation
        self.internal_resistance *= (1 + np.random.normal(0, 0.05))  # 5% variation
    
    def update(self, current_flow, time_step):
        """Update battery state based on current draw and time step (in seconds)"""
        self.current_flow = current_flow
        
        # Calculate voltage drop due to internal resistance
        voltage_drop = current_flow * self.internal_resistance
        
        # Update voltage based on SoC and load (simplified model)
        soc_factor = 1 - (1 - self.state_of_charge/100)**0.9  # non-linear relation
        self.current_voltage = self.min_voltage + (self.max_voltage - self.min_voltage) * soc_factor - voltage_drop
        
        # Bound voltage
        self.current_voltage = max(min(self.current_voltage, self.max_voltage), self.min_voltage)
        
        # Calculate energy
        energy_change = current_flow * self.current_voltage * time_step / 3600  # in mWh
        
        # Update state of charge
        soc_change = energy_change / (self.capacity * self.max_voltage / 1000) * 100
        self.state_of_charge -= soc_change
        self.state_of_charge = max(min(self.state_of_charge, 100), 0)
        
        # Calculate heat generation (I²R losses)
        heat_generation = current_flow**2 * self.internal_resistance
        
        # Update temperature using thermal model
        ambient_temp = 25  # degrees Celsius
        cooling_effect = (self.temperature - ambient_temp) / self.thermal_resistance
        temp_change = (heat_generation - cooling_effect) * time_step / self.heat_capacity
        self.temperature += temp_change
        
        # Update cell health (simplified aging model)
        if current_flow < 0:  # Only count discharge
            cycle_wear = abs(soc_change) / 100 * 0.002  # 0.2% degradation per full cycle
            temp_stress = max(0, (self.temperature - 35) / 10) * 0.01  # temperature stress
            self.health -= cycle_wear + temp_stress
            self.health = max(self.health, 0)
            
            # As health decreases, increase internal resistance and decrease capacity
            capacity_factor = 0.7 + 0.3 * (self.health / 100)  # capacity falls to 70% at end of life
            self.capacity = 3200 * capacity_factor
            self.internal_resistance = 0.02 * (2 - capacity_factor)  # resistance increases as health decreases
        
        return {
            'voltage': self.current_voltage,
            'soc': self.state_of_charge,
            'temperature': self.temperature,
            'health': self.health
        }

class BatteryPack:
    """Simulation of a battery pack consisting of multiple cells"""
    
    def __init__(self, cells_in_series=10, cells_in_parallel=5):
        """Initialize a battery pack with specified configuration"""
        self.cells_in_series = cells_in_series
        self.cells_in_parallel = cells_in_parallel
        self.total_cells = cells_in_series * cells_in_parallel
        
        # Create individual cells
        self.cells = []
        for i in range(self.total_cells):
            # Add slight variations to cells to simulate manufacturing differences
            cycle_count = np.random.randint(0, 20)  # Some cells might have different cycle counts
            self.cells.append(BatteryCell(cycle_count=cycle_count))
        
        # Organize cells in series-parallel configuration
        self.cell_matrix = np.array(self.cells).reshape(cells_in_series, cells_in_parallel)
        
        # Pack level properties
        self.pack_voltage = cells_in_series * self.cells[0].max_voltage
        self.pack_capacity = cells_in_parallel * self.cells[0].capacity  # in mAh
        
        # Logging data
        self.data_log = {
            'timestamp': [],
            'pack_voltage': [],
            'pack_current': [],
            'pack_soc': [],
            'min_cell_voltage': [],
            'max_cell_voltage': [],
            'voltage_imbalance': [],
            'min_temperature': [],
            'max_temperature': [],
            'avg_temperature': [],
            'pack_health': []
        }
    
    def update(self, pack_current, time_step):
        """Update all cells in the pack with the given current"""
        # Distribute current among parallel cells (ideally equal, but adjust based on cell resistance)
        cell_voltages = np.zeros((self.cells_in_series, self.cells_in_parallel))
        cell_temperatures = np.zeros((self.cells_in_series, self.cells_in_parallel))
        cell_socs = np.zeros((self.cells_in_series, self.cells_in_parallel))
        cell_healths = np.zeros((self.cells_in_series, self.cells_in_parallel))
        
        # Current per cell (assuming perfect current sharing for simplicity)
        current_per_cell = pack_current / self.cells_in_parallel
        
        # Update each cell
        for i in range(self.cells_in_series):
            for j in range(self.cells_in_parallel):
                cell_state = self.cell_matrix[i, j].update(current_per_cell, time_step)
                cell_voltages[i, j] = cell_state['voltage']
                cell_temperatures[i, j] = cell_state['temperature']
                cell_socs[i, j] = cell_state['soc']
                cell_healths[i, j] = cell_state['health']
        
        # Calculate series string voltages (sum voltages in each series)
        series_voltages = np.sum(cell_voltages, axis=0)
        
        # Calculate pack voltage (average of series string voltages for simplicity)
        self.pack_voltage = np.mean(series_voltages)
        
        # Calculate pack SoC (average of all cells)
        self.pack_soc = np.mean(cell_socs)
        
        # Calculate health metrics
        self.pack_health = np.mean(cell_healths)
        
        # Log data
        self.data_log['timestamp'].append(datetime.now())
        self.data_log['pack_voltage'].append(self.pack_voltage)
        self.data_log['pack_current'].append(pack_current)
        self.data_log['pack_soc'].append(self.pack_soc)
        self.data_log['min_cell_voltage'].append(np.min(cell_voltages))
        self.data_log['max_cell_voltage'].append(np.max(cell_voltages))
        self.data_log['voltage_imbalance'].append(np.max(cell_voltages) - np.min(cell_voltages))
        self.data_log['min_temperature'].append(np.min(cell_temperatures))
        self.data_log['max_temperature'].append(np.max(cell_temperatures))
        self.data_log['avg_temperature'].append(np.mean(cell_temperatures))
        self.data_log['pack_health'].append(self.pack_health)
        
        return {
            'pack_voltage': self.pack_voltage,
            'pack_soc': self.pack_soc,
            'min_cell_voltage': np.min(cell_voltages),
            'max_cell_voltage': np.max(cell_voltages),
            'voltage_imbalance': np.max(cell_voltages) - np.min(cell_voltages),
            'min_temperature': np.min(cell_temperatures),
            'max_temperature': np.max(cell_temperatures),
            'avg_temperature': np.mean(cell_temperatures),
            'pack_health': self.pack_health
        }
    
    def log_to_csv(self, filename='battery_data.csv'):
        """Save logged data to CSV file"""
        df = pd.DataFrame(self.data_log)
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")

class BatteryManagementSystem:
    """Battery Management System for monitoring and controlling a battery pack"""
    
    def __init__(self, battery_pack):
        """Initialize BMS with a battery pack to manage"""
        self.battery_pack = battery_pack
        self.is_charging = False
        self.fault_detected = False
        self.warnings = []
        
        # Safety thresholds
        self.max_temperature = 45  # degrees Celsius
        self.min_cell_voltage = 2.9  # volts
        self.max_cell_voltage = 4.15  # volts (slightly below max to extend life)
        self.max_voltage_imbalance = 0.15  # volts
        self.min_soc = 10  # percentage
        self.max_soc = 90  # percentage (avoid full charge for longevity)
        
        # Log data
        self.status_log = []
        
        # Create log directory
        if not os.path.exists('logs'):
            os.makedirs('logs')
    
    def monitor(self, pack_state):
        """Monitor battery pack parameters and detect faults"""
        self.warnings = []
        self.fault_detected = False
        
        # Check temperature
        if pack_state['max_temperature'] > self.max_temperature:
            self.warnings.append(f"WARNING: High temperature detected: {pack_state['max_temperature']:.1f}°C")
            if pack_state['max_temperature'] > self.max_temperature + 10:
                self.fault_detected = True
                self.warnings.append("FAULT: Critical temperature exceeded!")
        
        # Check voltage imbalance
        if pack_state['voltage_imbalance'] > self.max_voltage_imbalance:
            self.warnings.append(f"WARNING: Cell imbalance detected: {pack_state['voltage_imbalance']:.2f}V")
            if pack_state['voltage_imbalance'] > self.max_voltage_imbalance * 2:
                self.fault_detected = True
                self.warnings.append("FAULT: Critical cell imbalance!")
        
        # Check cell voltages
        if pack_state['min_cell_voltage'] < self.min_cell_voltage:
            self.warnings.append(f"WARNING: Low cell voltage: {pack_state['min_cell_voltage']:.2f}V")
            if pack_state['min_cell_voltage'] < self.min_cell_voltage - 0.2:
                self.fault_detected = True
                self.warnings.append("FAULT: Critical low cell voltage!")
        
        if pack_state['max_cell_voltage'] > self.max_cell_voltage:
            self.warnings.append(f"WARNING: High cell voltage: {pack_state['max_cell_voltage']:.2f}V")
            if pack_state['max_cell_voltage'] > self.max_cell_voltage + 0.1:
                self.fault_detected = True
                self.warnings.append("FAULT: Critical high cell voltage!")
        
        # Check SoC
        if pack_state['pack_soc'] < self.min_soc:
            self.warnings.append(f"WARNING: Low state of charge: {pack_state['pack_soc']:.1f}%")
        
        # Log status
        status = {
            'timestamp': datetime.now(),
            'pack_soc': pack_state['pack_soc'],
            'pack_voltage': pack_state['pack_voltage'],
            'max_temperature': pack_state['max_temperature'],
            'voltage_imbalance': pack_state['voltage_imbalance'],
            'is_charging': self.is_charging,
            'warnings': self.warnings,
            'fault_detected': self.fault_detected,
            'pack_health': pack_state['pack_health']
        }
        self.status_log.append(status)
        
        return status
    
    def control_charging(self, pack_state):
        """Determine charging parameters based on pack state"""
        if self.fault_detected:
            return 0  # No charging during faults
        
        if not self.is_charging:
            return 0
        
        # Determine charging current based on SoC and temperature
        base_charge_current = 10  # Amperes
        
        # Reduce current at high SoC
        if pack_state['pack_soc'] > 80:
            base_charge_current *= (90 - pack_state['pack_soc']) / 10
        
        # Reduce current at high temperature
        if pack_state['max_temperature'] > 35:
            temp_factor = max(0, (self.max_temperature - pack_state['max_temperature']) / 10)
            base_charge_current *= temp_factor
        
        # Stop charging if SoC is at max
        if pack_state['pack_soc'] >= self.max_soc:
            self.is_charging = False
            return 0
            
        return max(0, base_charge_current)  # Ensure positive current
    
    def control_discharging(self, pack_state, requested_current):
        """Determine if requested discharge current is safe"""
        if self.fault_detected:
            return 0  # No discharging during faults
        
        # Limit current based on SoC
        if pack_state['pack_soc'] < 20:
            max_current = requested_current * (pack_state['pack_soc'] / 20)
        else:
            max_current = requested_current
        
        # Limit current based on temperature
        if pack_state['max_temperature'] > 40:
            temp_factor = max(0, (self.max_temperature - pack_state['max_temperature']) / 5)
            max_current *= temp_factor
        
        # Stop discharging if SoC is at min
        if pack_state['pack_soc'] <= self.min_soc:
            return 0
            
        return -min(abs(max_current), requested_current)  # Ensure negative current (discharge)
    
    def balance_cells(self, pack_state):
        """Calculate cell balancing requirements"""
        # Simple balancing strategy: identify cells that need balancing
        cells_to_balance = []
        
        if pack_state['voltage_imbalance'] > 0.05:  # Only balance if imbalance is significant
            # In a real BMS we would identify specific cells, but for simulation we just report
            cells_to_balance.append(f"Cells with voltage > {pack_state['max_cell_voltage'] - 0.05:.2f}V")
        
        return cells_to_balance
    
    def generate_report(self, filename='bms_report.txt'):
        """Generate a report of BMS performance"""
        with open(os.path.join('logs', filename), 'w') as f:
            f.write("===== Battery Management System Report =====\n")
            f.write(f"Report generated: {datetime.now()}\n\n")
            
            # Overall statistics
            if len(self.status_log) > 0:
                avg_soc = np.mean([s['pack_soc'] for s in self.status_log])
                avg_temp = np.mean([s['max_temperature'] for s in self.status_log])
                avg_imbalance = np.mean([s['voltage_imbalance'] for s in self.status_log])
                latest_health = self.status_log[-1]['pack_health']
                
                f.write(f"Overall statistics:\n")
                f.write(f"- Average SoC: {avg_soc:.1f}%\n")
                f.write(f"- Average max temperature: {avg_temp:.1f}°C\n")
                f.write(f"- Average voltage imbalance: {avg_imbalance:.3f}V\n")
                f.write(f"- Current pack health: {latest_health:.1f}%\n\n")
            
            # Fault counts
            fault_count = sum(1 for s in self.status_log if s['fault_detected'])
            warning_count = sum(len(s['warnings']) for s in self.status_log)
            
            f.write(f"Safety statistics:\n")
            f.write(f"- Total faults detected: {fault_count}\n")
            f.write(f"- Total warnings issued: {warning_count}\n\n")
            
            # Recent warnings
            f.write("Most recent warnings:\n")
            for status in reversed(self.status_log[-10:]):
                if status['warnings']:
                    f.write(f"- {status['timestamp']}: {' | '.join(status['warnings'])}\n")
            
            f.write("\n===== End of Report =====\n")
        
        print(f"Report saved to logs/{filename}")

def run_simulation():
    """Run a battery simulation with typical usage patterns"""
    # Create battery pack
    battery_pack = BatteryPack(cells_in_series=12, cells_in_parallel=4)
    
    # Create BMS
    bms = BatteryManagementSystem(battery_pack)
    
    # Simulation parameters
    simulation_duration = 24 * 3600  # 24 hours in seconds
    time_step = 60  # 1 minute steps
    
    print("Starting Battery Management System Simulation...")
    print(f"Battery Pack: {battery_pack.cells_in_series}S{battery_pack.cells_in_parallel}P configuration")
    print(f"Total capacity: {battery_pack.pack_capacity / 1000:.1f} Ah")
    print(f"Nominal voltage: {battery_pack.pack_voltage:.1f}V")
    
    # Usage profiles (time in seconds, current in amperes)
    usage_profiles = [
        {'start': 0, 'end': 2 * 3600, 'current': -5},  # Morning discharge
        {'start': 2 * 3600, 'end': 8 * 3600, 'current': 0},  # Rest
        {'start': 8 * 3600, 'end': 10 * 3600, 'current': -15},  # Heavy use
        {'start': 10 * 3600, 'end': 12 * 3600, 'current': -2},  # Light use
        {'start': 12 * 3600, 'end': 14 * 3600, 'current': 0},  # Rest
        {'start': 14 * 3600, 'end': 16 * 3600, 'current': -10},  # Medium use
        {'start': 16 * 3600, 'end': 18 * 3600, 'current': 15}  # Charging
    ]
    
    # Run simulation
    current_time = 0
    while current_time < simulation_duration:
        # Determine current based on usage profile
        requested_current = 0
        for profile in usage_profiles:
            if profile['start'] <= current_time % (24 * 3600) < profile['end']:
                requested_current = profile['current']
                break
        
        # Set charging state if current is positive
        bms.is_charging = requested_current > 0
        
        # Determine actual current based on BMS controls
        if requested_current > 0:
            # Charging
            actual_current = bms.control_charging(battery_pack.update(0, 0))  # Get state without updating
        else:
            # Discharging
            actual_current = bms.control_discharging(battery_pack.update(0, 0), abs(requested_current))
        
        # Update battery pack
        pack_state = battery_pack.update(actual_current, time_step)
        
        # Monitor and control via BMS
        bms_status = bms.monitor(pack_state)
        balancing = bms.balance_cells(pack_state)
        
        # Print status at regular intervals
        if current_time % (3600) == 0:  # Every hour
            print(f"\nTime: {current_time // 3600}h")
            print(f"SoC: {pack_state['pack_soc']:.1f}%, Voltage: {pack_state['pack_voltage']:.2f}V")
            print(f"Temperature: {pack_state['avg_temperature']:.1f}°C (max: {pack_state['max_temperature']:.1f}°C)")
            print(f"Current: {actual_current:.2f}A")
            
            if bms_status['warnings']:
                print("Warnings:", bms_status['warnings'])
            
            if balancing:
                print("Cell balancing active:", balancing)
        
        # increment time
        current_time += time_step
    
    # Generate report
    bms.generate_report()
    
    # Save data log
    battery_pack.log_to_csv(os.path.join('logs', 'battery_data.csv'))
    
    # Visualize results
    visualize_results(battery_pack.data_log)

def visualize_results(data_log):
    """Create visualization of battery data"""
    # Convert data to DataFrame
    df = pd.DataFrame(data_log)
    
    # Create figure
    plt.figure(figsize=(16, 12))
    
    # Plot 1: SoC and Voltage
    plt.subplot(3, 1, 1)
    plt.plot(range(len(df)), df['pack_soc'], 'b-', label='State of Charge (%)')
    plt.ylabel('State of Charge (%)')
    plt.legend(loc='upper left')
    
    plt.twinx()
    plt.plot(range(len(df)), df['pack_voltage'], 'r-', label='Pack Voltage (V)')
    plt.ylabel('Voltage (V)')
    plt.legend(loc='upper right')
    plt.title('Battery State of Charge and Voltage')
    
    # Plot 2: Current
    plt.subplot(3, 1, 2)
    plt.plot(range(len(df)), df['pack_current'], 'g-', label='Current (A)')
    plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    plt.fill_between(range(len(df)), df['pack_current'], 0, where=(df['pack_current'] > 0), 
                     color='g', alpha=0.3, label='Charging')
    plt.fill_between(range(len(df)), df['pack_current'], 0, where=(df['pack_current'] < 0), 
                     color='r', alpha=0.3, label='Discharging')
    plt.ylabel('Current (A)')
    plt.legend()
    plt.title('Battery Current')
    
    # Plot 3: Temperature and Cell Balance
    plt.subplot(3, 1, 3)
    plt.plot(range(len(df)), df['avg_temperature'], 'r-', label='Avg Temperature (°C)')
    plt.fill_between(range(len(df)), df['min_temperature'], df['max_temperature'], 
                     color='r', alpha=0.2, label='Temperature Range')
    plt.ylabel('Temperature (°C)')
    plt.legend(loc='upper left')
    
    plt.twinx()
    plt.plot(range(len(df)), df['voltage_imbalance'], 'b-', label='Voltage Imbalance (V)')
    plt.ylabel('Voltage Imbalance (V)')
    plt.legend(loc='upper right')
    plt.title('Battery Temperature and Cell Imbalance')
    
    plt.tight_layout()
    plt.savefig(os.path.join('logs', 'battery_performance.png'))
    plt.close()
    
    # Create another figure for health metrics
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(df)), df['pack_health'], 'g-', label='Pack Health (%)')
    plt.ylabel('Health (%)')
    plt.xlabel('Time (minutes)')
    plt.title('Battery Pack Health Over Time')
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join('logs', 'battery_health.png'))
    plt.close()
    
    print("Visualizations saved to logs/ directory")

if __name__ == "__main__":
    run_simulation()
