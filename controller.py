import importlib
import inspect 
from tabulate import tabulate
from prettytable import PrettyTable
from datetime import datetime
import os
import json

import executer

MALA_OUTPUT_PATH = os.path.join(".", "output", "")

#DEFINE
PROMPT = "MALA"
MODULE = ""

executed_processes = {}

def initialize(loaded_modules, universal_variables, tool_paths, modules_config):
    global modules, variables, tools, executed_processes, modules_config_path, module_mapping
    modules = loaded_modules
    module_mapping = {os.path.splitext(os.path.basename(path))[0]: path for path in modules}
    modules_config_path = modules_config
    variables = universal_variables
    tools = tool_paths
    executed_processes = {}

#help command
def help():
    print("\nAvailable commands:")
    for command, handler in command_handlers.items():
        command_description = handler.get("description", "No description")
        print(f"{command} - {command_description}")

#set variable
def set_variable(args):
    global variables
    if len(args) < 2:
        print("Usage: SET <variable> <value>")
        return
    selected_var = args[0]
    new_value = " ".join(args[1:])

    for variable_type, variable_options in variables.items():
        if selected_var in variable_options and variable_type == "common_variables":
            variable_options[selected_var]["Value"] = new_value
            print(f"[*] {selected_var} set to: {new_value}")
            return
        elif selected_var in variable_options and variable_type == "module_variables":
            if new_module.validate_input(selected_var, new_value):
                variable_options[selected_var]["Value"] = new_value
                print(f"[*] {selected_var} set to: {new_value}")
            return
    print(f"[*] {selected_var} is not a valid variable. use `variable` command to see available options")
    
#clear variable
def clear_variable(args):
    global variables
    selected_var = args[0]
    new_value = ""

    for variable_type, variable_options in variables.items():
        if selected_var in variable_options:
            variable_options[selected_var]["Value"] = new_value
            print(f"[*] {selected_var} cleared")
            return
    print(f"[*] {selected_var} does not exist, use `variables` command to see available options")

#show all variables and their values
def show_variables():
    common_vars = variables["common_variables"]
    module_vars = variables["module_variables"]

    common_table = [["Name", "Value", "Description"]]
    for var, details in common_vars.items():
        common_table.append([var, details["Value"], details["Description"], details["Required"]])

    module_table = [["Name", "Value", "Description", "Required"]]
    for var, details in module_vars.items():
        module_table.append([var, details["Value"], details["Description"], details["Required"]])

    print("\n--Common Options--\n")
    print(tabulate(common_table, headers="firstrow", tablefmt="pretty"))
    print("\n--Module Options--\n")
    print(tabulate(module_table, headers="firstrow", tablefmt="pretty"))

#show available modules
def show_modules(arg=[""]):
    module_names = list(module_mapping.keys())
    module_names.remove("base_module")
    with open(modules_config_path) as file:
        module_menu_data = json.load(file)

    if arg[0] == "add":
        # Compare items in loaded_modules with keys in the JSON file
        for module in module_names:
            if module not in module_menu_data:
                # Add new entry to the JSON file
                module_menu_data[module] = {
                    "Description": "",
                    "Tagging": [""]
                }

        # Write the updated JSON data back to the file
        with open(modules_config_path, 'w') as file:
            json.dump(module_menu_data, file, indent=4)
        print("\nModules added to config")
        return
    
    print("\n")
    table = PrettyTable()
    table.field_names = ["Module Name", "Module Description", "Module Tagging"]
    table.max_table_width=120
    for module , module_info in module_menu_data.items():
        if module in module_names:
            description = module_info["Description"]
            tagging = module_info["Tagging"][0] if module_info["Tagging"] else "None"

            table.add_row([module, description, tagging])

    print(table)

#select module to use
def use_module(arg):
    global variables, MODULE, new_module, class_name

    if not len(arg):
        print ("This option requires arguments")
        return
    
    selected_module = arg[0]
    variables["module_variables"].clear()
    try:
        module_import_path = module_mapping[selected_module].replace('\\', '.').replace('/', '.').replace(".py","").lstrip('.')
        print(module_import_path)
        module = importlib.import_module(module_import_path)
        module_class = inspect.getmembers(module, inspect.isclass)
        if module_class:
            class_name, class_obj = module_class[-1]
            new_module = class_obj(variables)
            MODULE = "(" + class_name + ")"
            return new_module
    except KeyError:
        print(f"\nModule '{selected_module}' not found.")

#execute the module
def execute():
    global MALA_OUTPUT_FILE
    new_module.initialize_before_run(tools,variables)
    command_list = new_module.get_command_list()
    if not command_list:
        print("\nFailed to run. No module selected or compulsory options were not set.")
        return
    elif command_list == "Handled":
        return
    
    #Create the actual command from a list
    vanilla_command = " ".join(command_list)

    curr_time = datetime.now()
    MALA_OUTPUT_FILE = MALA_OUTPUT_PATH + class_name + "_" + str(curr_time.strftime("%Y%m%d_%H%M%S_%f"))
    #attempt to execute command and get pid

    pid = executer.execute_command(vanilla_command,MALA_OUTPUT_FILE)
    if pid:
        executed_processes[pid] = {"module":class_name, "command":vanilla_command, "status":"Running", "time":curr_time, "output":MALA_OUTPUT_FILE}

#show list of executed commands
def show_status():
    #Get status of processes
    for pid in executed_processes.keys():
        if executed_processes[pid]["status"] in [None, "Running"]:
            getUpdate_process_status(pid)
        continue

    #Create the table of executed processes
    process_table = [["Index","PID","Module","Command","Status","Time","Output"]]
    index = 0
    for pid, pid_info in executed_processes.items():
        index += 1
        process_table.append([index, pid, pid_info["module"], pid_info["command"], pid_info["status"], pid_info["time"].strftime("%Y%m%d %H:%M"), pid_info["output"]])

    print("\n--Executed commands--\n")
    print(tabulate(process_table, headers="firstrow", tablefmt="pretty"))
    return 0

#check status of a running command or all running commands
def show_output(arg):
    if not len(arg):
        print ("This option requires arguments")
        return
    
    index = abs(int(arg[0]))
    if index > len(executed_processes):
        print("Invalid index")
        return
    #Search executed_process dict for the index
    pid = list(executed_processes.keys())[index-1]
    #pass file name to get status
    executer.get_command_output(executed_processes[pid]["output"])

    return 0

#kill process
def kill_process(arg=""):
    if arg[0].strip() == "all":
        user_confirmation = validate_user_confirm("This will kill all running processes. Continue?")
        if not user_confirmation.lower().startswith("y"):
            print("Nothing was killed")
            return
        kill_all_processes()
        return
    try:
        int(arg[0])
    except:
        print("Invalid argument, either `kill all` or `kill <process index>`")
        return
    index = abs(int(arg[0]))
    if index > len(executed_processes):
        print("Invalid index")
        return
    
    kill_pid = list(executed_processes.keys())[index-1]
    user_confirmation = validate_user_confirm(f"Kill process {kill_pid['module']} started at {kill_pid['time']}?")
    if not user_confirmation.lower().startswith("y"):
        print("Nothing was killed")
        return
    executer.kill_process(kill_pid)
    getUpdate_process_status(kill_pid, True)
    return 

#remove process from executed process list
def clear_process(arg):
    process_removal_list = []
    if arg[0] == 'all':
        user_confirmation = validate_user_confirm("This will clear all processes in executed list. Continue?")
        if not user_confirmation.lower().startswith("y"):
            print("Nothing was cleared")
            return
        for pid, pid_info in executed_processes.items():
            if not (pid_info["status"] == "Running" and getUpdate_process_status(pid) == "Running"):
                process_removal_list.append(pid)
                continue
            user_kill_confirm = validate_user_confirm(f"{pid_info['module']} started at {pid_info['time']} is still running. Kill before clearing?")
            if not user_kill_confirm.lower().startswith("y"):
                print("Skipping... This process will not be killed or cleared")
                continue
            executer.kill_process(pid)
            getUpdate_process_status(pid, True)
            process_removal_list.append(pid)
        for process in process_removal_list:
            executed_processes.pop(process)
        return

    try:
        int(arg[0])
    except ValueError:
        print("Invalid argument, either `kill all` or `kill <process index>`")
        return
    index = abs(int(arg[0]))
    if index > len(executed_processes):
        print("Invalid index")
        return
    
    clear_process = list(executed_processes.keys())[index-1]
    clear_process_info = executed_processes[clear_process]
    if not (clear_process_info["status"] == "Running" and getUpdate_process_status(clear_process) == "Running"):
        executed_processes.pop(clear_process)
    else:
        user_kill_confirm = validate_user_confirm(f"{clear_process_info['module']} started at {clear_process_info['time']} is still running. Kill before clearing?")
        if not user_kill_confirm.lower().startswith("y"):
            print("Nothing was be cleared")
            return
        executer.kill_process(clear_process)
        executed_processes.pop(clear_process)
        print(f"process #{index} has been cleared")

#handle for when unknown command is given
def command_not_found(user_input):
    print(f"\nUnknown command: {user_input}")
    help()

# Dictionary mapping commands to functions and their arguments
command_handlers = {
    "help": {
        "function": help,
        "description": "Prints this menu",
        "valid_inputs": ["help"]
    },
    "set": {
        "function": set_variable,
        "description": "Set a variable",
        "valid_inputs": ["set"]
    },
    "clear": {
        "function": clear_variable,
        "description": "Clear the variable value",
        "valid_inputs": ["clear"]
    },
    "variables": {
        "function": show_variables,
        "description": "Show variables",
        "valid_inputs": ["variables", "options", "vars"]
    },
    "modules": {
        "function": show_modules,
        "description": "Show all available modules",
        "valid_inputs": ["modules", "mods"]
    },
    "use": {
        "function": use_module,
        "description": "Set context to a module",
        "valid_inputs": ["use"]
    },
    "run": {
        "function": execute,
        "description": "Execute the current command built from the module",
        "valid_inputs": ["run"]
    },
    "status": {
        "function": show_status,
        "description": "Show command/ process statuses",
        "valid_inputs": ["status","show-run", "executed"]
    },
    "show": {
        "function": show_output,
        "description": "show output of commands",
        "valid_inputs": ["show","output"]
    },
    "kill": {
        "function": kill_process,
        "description": "`kill <process-index>` or `kill all`",
        "valid_inputs": ["kill","stop"]
    },
    "clear": {
        "function": clear_process,
        "description": "clear completed processes from executed process list",
        "valid_inputs": ["clear"]
    },    
    "exit": {
        "function": None,
        "description": "exit program",
        "valid_inputs": ["exit","quit"]
    },    

}

def getUpdate_process_status(check_pid, killed = False):
    status = "Killed" if killed else executer.get_process_status(check_pid)
    executed_processes[check_pid]["status"] = status
    return executed_processes[check_pid]["status"]

def kill_all_processes():
    #Get status of processes
    for pid, pid_info in executed_processes.items():
        if pid_info["status"] != "Completed" and getUpdate_process_status(pid) == "Running":
            #Kill process if its still running
            executer.kill_process(pid)
            #Update executed processes info
            getUpdate_process_status(pid, True)

def validate_user_confirm(confirm_message):
    valid_confirmational_inputs = ['y','yes','n','no']
    user_confirmation_input = None
    while True:
        user_confirmation_input = input(confirm_message + " (Y/N):")
        if not user_confirmation_input.lower() in valid_confirmational_inputs:
            print("Invalid input")
            continue
        break
    return user_confirmation_input        

        
# Main
def main():
    while True:
        try:
            user_input = input("\n" + PROMPT + MODULE + " > ").strip()
            command = user_input.split()[0].lower()
            args = user_input.split()[1:]
            matched_command = None
            matched_command = [command_key for command_key, command_info in command_handlers.items() if command in command_info["valid_inputs"]] 
            if not matched_command:
                command_not_found(user_input)
            if matched_command[0] == "exit":
                kill_all_processes()
                break
            if matched_command:
                command_function = command_handlers[matched_command[0]].get("function")
                command_function(args) if len(args) != 0 else command_function()
            
        except KeyboardInterrupt:
            print("\nCtrl+C pressed. Exiting...")
            kill_all_processes()
            
            break

        except:
            continue

