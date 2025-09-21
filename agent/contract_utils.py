# =============================================================================
# COMPILATION AND VALIDATION FUNCTIONS
# =============================================================================

import json
import os
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

try:
    from solcx import compile_source, install_solc, get_installed_solc_versions, set_solc_version
    from web3 import Web3
    from eth_utils import to_checksum_address
    from eth_abi import encode
except ImportError:
    print("Warning: Blockchain libraries not installed.")


def compile_contract(contract_code: str, contract_name: str = "CustomContract") -> Dict[str, Any]:
    """Use py-solc-x to compile Solidity code and return compilation results."""
    try:
        # Ensure solidity compiler is installed
        try:
            installed_versions = get_installed_solc_versions()
            if not installed_versions:
                install_solc(version='latest')
                set_solc_version('latest')
            else:
                set_solc_version(installed_versions[0])
        except Exception as e:
            return {"status": "error", "error_message": f"Failed to setup Solidity compiler: {str(e)}"}
        
        # Compile the contract
        compiled_sol = compile_source(
            contract_code,
            output_values=['abi', 'bin', 'bin-runtime', 'ast', 'metadata'],
            solc_version=None,
            allow_paths=None
        )
        
        # Extract contract information
        contract_id = None
        for key in compiled_sol.keys():
            if contract_name in key:
                contract_id = key
                break
        
        if not contract_id:
            contract_id = list(compiled_sol.keys())[0]
        
        contract_interface = compiled_sol[contract_id]
        
        # Calculate contract size
        bytecode = contract_interface['bin']
        contract_size = len(bytecode) // 2  # Convert hex to bytes
        
        # Extract ABI functions
        abi = contract_interface['abi']
        functions = [item for item in abi if item['type'] == 'function']
        events = [item for item in abi if item['type'] == 'event']
        
        return {
            "status": "success",
            "data": {
                "bytecode": bytecode,
                "runtime_bytecode": contract_interface.get('bin-runtime', ''),
                "abi": abi,
                "contract_size_bytes": contract_size,
                "contract_size_kb": round(contract_size / 1024, 2),
                "is_over_size_limit": contract_size > 24576,  # 24KB limit
                "function_count": len(functions),
                "event_count": len(events),
                "functions": [f"{func['name']}({','.join([p['type'] for p in func.get('inputs', [])])})" for func in functions],
                "events": [f"{event['name']}({','.join([p['type'] for p in event.get('inputs', [])])})" for event in events],
                "metadata": contract_interface.get('metadata', {}),
                "compilation_warnings": []
            }
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Parse common compilation errors
        if "ParserError" in error_msg:
            return {"status": "error", "error_type": "syntax_error", "error_message": f"Syntax error in contract: {error_msg}"}
        elif "TypeError" in error_msg:
            return {"status": "error", "error_type": "type_error", "error_message": f"Type error in contract: {error_msg}"}
        elif "DeclarationError" in error_msg:
            return {"status": "error", "error_type": "declaration_error", "error_message": f"Declaration error: {error_msg}"}
        else:
            return {"status": "error", "error_type": "compilation_error", "error_message": f"Compilation failed: {error_msg}"}


def analyze_gas_usage(bytecode: str, abi_json: str, contract_code: str = "") -> Dict[str, Any]:
    """Estimate deployment and function call gas costs."""
    try:
        # Parse ABI JSON string to list
        import json
        abi = json.loads(abi_json) if isinstance(abi_json, str) else abi_json
        
        # Estimate deployment gas
        deployment_gas = len(bytecode) // 2 * 200  # Rough estimate: 200 gas per byte
        
        # Analyze functions for gas estimates
        function_estimates = {}
        
        for item in abi:
            if item['type'] == 'function':
                func_name = item['name']
                state_mutability = item.get('stateMutability', 'nonpayable')
                
                # Base gas estimates by function type
                if state_mutability in ['view', 'pure']:
                    base_gas = 500  # Read-only functions
                elif 'mint' in func_name.lower():
                    base_gas = 50000  # Minting operations
                elif 'transfer' in func_name.lower():
                    base_gas = 21000  # Transfer operations
                elif 'approve' in func_name.lower():
                    base_gas = 45000  # Approval operations
                else:
                    base_gas = 25000  # Default for state-changing functions
                
                # Additional gas for complex operations
                if contract_code:
                    func_lines = []
                    in_function = False
                    brace_count = 0
                    
                    for line in contract_code.split('\n'):
                        if f'function {func_name}' in line:
                            in_function = True
                        
                        if in_function:
                            func_lines.append(line)
                            brace_count += line.count('{') - line.count('}')
                            
                            if brace_count == 0 and '{' in ''.join(func_lines):
                                break
                    
                    func_body = '\n'.join(func_lines)
                    
                    # Add gas for specific operations
                    if 'emit ' in func_body:
                        base_gas += 1000 * func_body.count('emit ')
                    if '.call(' in func_body:
                        base_gas += 10000 * func_body.count('.call(')
                    if 'require(' in func_body:
                        base_gas += 500 * func_body.count('require(')
                    if 'mapping(' in func_body:
                        base_gas += 5000 * func_body.count('mapping(')
                
                function_estimates[func_name] = {
                    "estimated_gas": base_gas,
                    "state_mutability": state_mutability,
                    "gas_category": "low" if base_gas < 30000 else "medium" if base_gas < 60000 else "high"
                }
        
        # Gas optimization suggestions
        optimizations = []
        
        if deployment_gas > 1000000:
            optimizations.append("Contract is large. Consider splitting into multiple contracts or using libraries.")
        
        high_gas_functions = [name for name, data in function_estimates.items() if data["estimated_gas"] > 60000]
        if high_gas_functions:
            optimizations.append(f"High gas functions detected: {', '.join(high_gas_functions)}. Consider optimization.")
        
        if contract_code:
            if contract_code.count('for (') > 3:
                optimizations.append("Multiple loops detected. Consider batch processing or pagination.")
            if contract_code.count('mapping(') > 5:
                optimizations.append("Many mappings detected. Consider struct packing for gas efficiency.")
        
        return {
            "status": "success",
            "data": {
                "deployment_gas_estimate": deployment_gas,
                "deployment_cost_eth": deployment_gas * 20e-9,  # Assuming 20 gwei gas price
                "function_gas_estimates": function_estimates,
                "total_functions": len(function_estimates),
                "average_function_gas": sum(f["estimated_gas"] for f in function_estimates.values()) // len(function_estimates) if function_estimates else 0,
                "optimizations": optimizations,
                "gas_efficiency_score": max(0, 100 - len(optimizations) * 15)
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Gas analysis failed: {str(e)}"}


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def generate_test_suite(contract_code: str, abi_json: str, contract_name: str = "CustomContract") -> Dict[str, Any]:
    """Create basic unit tests using Web3.py framework."""
    try:
        # Parse ABI JSON string to list
        import json
        abi = json.loads(abi_json) if isinstance(abi_json, str) else abi_json
        
        # Extract functions from ABI
        functions = [item for item in abi if item['type'] == 'function']
        constructor = next((item for item in abi if item['type'] == 'constructor'), None)
        events = [item for item in abi if item['type'] == 'event']
        
        # Generate test file content
        test_content = f'''"""
Test suite for {contract_name}
Generated automatically by Smart Contract Generator
"""

import pytest
from web3 import Web3
from eth_tester import EthereumTester
from web3.providers.eth_tester import EthereumTesterProvider
import json

# Test configuration
@pytest.fixture
def w3():
    return Web3(EthereumTesterProvider(EthereumTester()))

@pytest.fixture
def contract_factory(w3):
    # Contract ABI
    abi = {json.dumps(abi, indent=2)}
    
    # Contract bytecode (replace with actual bytecode after compilation)
    bytecode = "0x608060405234801561001057600080fd5b50..."  # Placeholder
    
    return w3.eth.contract(abi=abi, bytecode=bytecode)

@pytest.fixture
def deployed_contract(w3, contract_factory):
    # Deploy contract with default parameters
    tx_hash = contract_factory.constructor(
        # Add constructor parameters here
    ).transact({{'from': w3.eth.accounts[0]}})
    
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return w3.eth.contract(address=tx_receipt.contractAddress, abi=contract_factory.abi)

# Basic deployment test
def test_contract_deployment(deployed_contract):
    """Test that contract deploys successfully."""
    assert deployed_contract.address is not None
    assert Web3.is_address(deployed_contract.address)

'''
        
        # Generate tests for each function
        for func in functions:
            func_name = func['name']
            state_mutability = func.get('stateMutability', 'nonpayable')
            inputs = func.get('inputs', [])
            outputs = func.get('outputs', [])
            
            # Generate test parameters
            test_params = []
            for input_param in inputs:
                param_type = input_param['type']
                if param_type == 'uint256':
                    test_params.append('100')
                elif param_type == 'address':
                    test_params.append('w3.eth.accounts[1]')
                elif param_type == 'string':
                    test_params.append('"test_string"')
                elif param_type == 'bool':
                    test_params.append('True')
                else:
                    test_params.append('0')  # Default fallback
            
            param_str = ', '.join(test_params)
            
            if state_mutability in ['view', 'pure']:
                # Read-only function test
                test_content += f'''
def test_{func_name}(deployed_contract):
    """Test {func_name} function."""
    result = deployed_contract.functions.{func_name}({param_str}).call()
    assert result is not None
    # Add specific assertions based on expected behavior

'''
            else:
                # State-changing function test
                test_content += f'''
def test_{func_name}(w3, deployed_contract):
    """Test {func_name} function."""
    # Get initial state
    initial_state = None  # Add state check if applicable
    
    # Execute function
    tx_hash = deployed_contract.functions.{func_name}({param_str}).transact({{'from': w3.eth.accounts[0]}})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Verify transaction success
    assert tx_receipt.status == 1
    
    # Verify state changes
    # Add assertions to check state changes
    
    # Check events if any
    # event_logs = deployed_contract.events.EventName().process_receipt(tx_receipt)
    # assert len(event_logs) > 0

'''
        
        # Add edge case tests
        test_content += '''
# Edge case tests
def test_unauthorized_access(w3, deployed_contract):
    """Test that unauthorized users cannot access restricted functions."""
    # Try calling owner-only functions from non-owner account
    with pytest.raises(Exception):
        # deployed_contract.functions.ownerOnlyFunction().transact({'from': w3.eth.accounts[1]})
        pass

def test_zero_values(deployed_contract):
    """Test functions with zero values."""
    # Add tests for zero amounts, addresses, etc.
    pass

def test_boundary_values(deployed_contract):
    """Test functions with boundary values."""
    # Add tests for maximum values, minimum values, etc.
    pass

def test_invalid_inputs(deployed_contract):
    """Test functions with invalid inputs."""
    # Add tests for invalid addresses, amounts, etc.
    pass
'''
        
        # Generate pytest configuration
        pytest_ini = '''[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
'''
        
        # Generate requirements for testing
        test_requirements = '''pytest>=7.0.0
web3>=6.0.0
eth-tester>=0.8.0
py-solc-x>=2.0.0
'''
        
        return {
            "status": "success",
            "data": {
                "test_file_content": test_content,
                "test_file_name": f"test_{contract_name.lower()}.py",
                "pytest_config": pytest_ini,
                "test_requirements": test_requirements,
                "test_functions_generated": len(functions) + 4,  # +4 for edge case tests
                "coverage_areas": [
                    "Contract deployment",
                    "Function execution",
                    "State changes",
                    "Event emission",
                    "Access control",
                    "Edge cases"
                ]
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Test generation failed: {str(e)}"}


def simulate_contract_deployment(contract_code: str, network: str = "ganache") -> Dict[str, Any]:
    """Deploy contract to test networks and return deployment information."""
    try:
        # Compile contract first
        compile_result = compile_contract(contract_code)
        if compile_result["status"] != "success":
            return compile_result
        
        compilation_data = compile_result["data"]
        abi = compilation_data["abi"]
        bytecode = compilation_data["bytecode"]
        
        # Set up Web3 connection based on network
        if network.lower() == "ganache":
            w3 = Web3(Web3.EthereumTesterProvider())
        elif network.lower() == "localhost":
            w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        else:
            return {"status": "error", "error_message": f"Unsupported network: {network}"}
        
        if not w3.is_connected():
            return {"status": "error", "error_message": f"Cannot connect to {network} network"}
        
        # Set default account
        if w3.eth.accounts:
            w3.eth.default_account = w3.eth.accounts[0]
            deployer_address = w3.eth.accounts[0]
        else:
            return {"status": "error", "error_message": "No accounts available for deployment"}
        
        # Create contract factory
        contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
        
        # Estimate gas for deployment
        try:
            gas_estimate = contract_factory.constructor().estimate_gas()
        except Exception:
            gas_estimate = 2000000  # Default gas limit
        
        # Deploy contract
        tx_hash = contract_factory.constructor().transact({
            'from': deployer_address,
            'gas': gas_estimate,
            'gasPrice': w3.to_wei('20', 'gwei')
        })
        
        # Wait for deployment
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if tx_receipt.status != 1:
            return {"status": "error", "error_message": "Contract deployment failed"}
        
        # Get deployed contract instance
        deployed_contract = w3.eth.contract(
            address=tx_receipt.contractAddress,
            abi=abi
        )
        
        # Calculate deployment cost
        gas_used = tx_receipt.gasUsed
        gas_price = w3.to_wei('20', 'gwei')  # Assuming 20 gwei
        deployment_cost_wei = gas_used * gas_price
        deployment_cost_eth = w3.from_wei(deployment_cost_wei, 'ether')
        
        return {
            "status": "success",
            "data": {
                "network": network,
                "contract_address": tx_receipt.contractAddress,
                "deployer_address": deployer_address,
                "transaction_hash": tx_hash.hex(),
                "block_number": tx_receipt.blockNumber,
                "gas_used": gas_used,
                "gas_estimate": gas_estimate,
                "deployment_cost_wei": deployment_cost_wei,
                "deployment_cost_eth": float(deployment_cost_eth),
                "contract_size_bytes": compilation_data["contract_size_bytes"],
                "abi": abi,
                "function_count": compilation_data["function_count"],
                "event_count": compilation_data["event_count"]
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Deployment simulation failed: {str(e)}"}


# =============================================================================
# DOCUMENTATION AND EXPLANATION FUNCTIONS
# =============================================================================

def generate_contract_documentation(contract_code: str, contract_name: str = "CustomContract") -> Dict[str, Any]:
    """Create NatSpec comments and comprehensive documentation."""
    try:
        lines = contract_code.split('\n')
        
        # Extract contract information
        contract_info = {
            "name": contract_name,
            "functions": [],
            "events": [],
            "modifiers": [],
            "state_variables": []
        }
        
        # Parse contract structure
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if line_stripped.startswith('function ') and 'internal' not in line and 'private' not in line:
                func_match = re.search(r'function\s+(\w+)\s*\(([^)]*)\)', line)
                if func_match:
                    func_name = func_match.group(1)
                    params = func_match.group(2)
                    
                    visibility = 'public' if 'public' in line else 'external' if 'external' in line else 'internal'
                    state_mutability = ''
                    if 'view' in line:
                        state_mutability = 'view'
                    elif 'pure' in line:
                        state_mutability = 'pure'
                    elif 'payable' in line:
                        state_mutability = 'payable'
                    
                    contract_info["functions"].append({
                        "name": func_name,
                        "parameters": params,
                        "visibility": visibility,
                        "state_mutability": state_mutability,
                        "line": i + 1
                    })
            
            elif line_stripped.startswith('event '):
                event_match = re.search(r'event\s+(\w+)\s*\(([^)]*)\)', line)
                if event_match:
                    contract_info["events"].append({
                        "name": event_match.group(1),
                        "parameters": event_match.group(2),
                        "line": i + 1
                    })
            
            elif line_stripped.startswith('modifier '):
                modifier_match = re.search(r'modifier\s+(\w+)', line)
                if modifier_match:
                    contract_info["modifiers"].append({
                        "name": modifier_match.group(1),
                        "line": i + 1
                    })
        
        # Generate comprehensive documentation
        doc_content = f"""# {contract_name} Documentation

## Overview
{contract_name} is a Solidity smart contract generated by the Smart Contract Generator.

## Contract Details
- **Name**: {contract_name}
- **Solidity Version**: ^0.8.19
- **License**: MIT

## Architecture

### Functions ({len(contract_info['functions'])})
"""
        
        for func in contract_info["functions"]:
            doc_content += f"""
#### `{func['name']}`
- **Visibility**: {func['visibility']}
- **State Mutability**: {func['state_mutability'] or 'nonpayable'}
- **Parameters**: `{func['parameters']}`
- **Description**: [Add description for {func['name']} function]
- **Usage Example**: 
  ```solidity
  // Example usage of {func['name']}
  contract.{func['name']}({func['parameters']});
  ```
"""
        
        if contract_info["events"]:
            doc_content += f"""
### Events ({len(contract_info['events'])})
"""
            for event in contract_info["events"]:
                doc_content += f"""
#### `{event['name']}`
- **Parameters**: `{event['parameters']}`
- **Description**: [Add description for {event['name']} event]
"""
        
        if contract_info["modifiers"]:
            doc_content += f"""
### Modifiers ({len(contract_info['modifiers'])})
"""
            for modifier in contract_info["modifiers"]:
                doc_content += f"""
#### `{modifier['name']}`
- **Description**: [Add description for {modifier['name']} modifier]
"""
        
        doc_content += """
## Security Considerations
- [List security considerations]
- [Mention access controls]
- [Highlight potential risks]

## Gas Optimization
- [List gas optimization techniques used]
- [Mention estimated gas costs]

## Testing
- [Describe testing approach]
- [List test scenarios covered]

## Deployment
- [Provide deployment instructions]
- [List required constructor parameters]

## License
This contract is released under the MIT License.
"""
        
        # Generate NatSpec comments for the contract
        natspec_contract = f'''/// @title {contract_name}
/// @author Smart Contract Generator
/// @notice This contract implements [describe main functionality]
/// @dev This contract uses OpenZeppelin libraries for security
'''
        
        # Generate function-level NatSpec
        natspec_functions = {}
        for func in contract_info["functions"]:
            natspec_functions[func["name"]] = f'''    /// @notice [Describe what this function does]
    /// @dev [Add implementation details]
    /// @param [Add parameter descriptions]
    /// @return [Add return value description]
'''
        
        return {
            "status": "success",
            "data": {
                "markdown_documentation": doc_content,
                "natspec_contract": natspec_contract,
                "natspec_functions": natspec_functions,
                "contract_structure": contract_info,
                "documentation_sections": [
                    "Overview",
                    "Contract Details", 
                    "Functions",
                    "Events",
                    "Security Considerations",
                    "Gas Optimization",
                    "Testing",
                    "Deployment"
                ]
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Documentation generation failed: {str(e)}"}


def explain_generated_code(contract_code: str) -> Dict[str, Any]:
    """Break down the contract into understandable sections and explain functionality."""
    try:
        lines = contract_code.split('\n')
        explanations = []
        
        current_section = None
        section_start = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Identify different sections
            if line_stripped.startswith('pragma solidity'):
                explanations.append({
                    "section": "Pragma Declaration",
                    "line_start": i + 1,
                    "line_end": i + 1,
                    "code": line_stripped,
                    "explanation": "Specifies the Solidity compiler version to use. The '^' symbol means any version compatible with this version.",
                    "importance": "critical"
                })
            
            elif line_stripped.startswith('import '):
                if current_section != "imports":
                    if current_section:
                        explanations[-1]["line_end"] = i
                    current_section = "imports"
                    explanations.append({
                        "section": "Import Statements",
                        "line_start": i + 1,
                        "code": line_stripped,
                        "explanation": "Imports OpenZeppelin contracts for standard implementations and security features.",
                        "importance": "high"
                    })
                else:
                    explanations[-1]["code"] += f"\n{line_stripped}"
            
            elif line_stripped.startswith('contract '):
                if current_section:
                    explanations[-1]["line_end"] = i
                current_section = "contract_declaration"
                contract_name = line_stripped.split()[1].split('(')[0]
                inheritance = ""
                if ' is ' in line_stripped:
                    inheritance = line_stripped.split(' is ')[1].split(' {')[0]
                
                explanations.append({
                    "section": "Contract Declaration",
                    "line_start": i + 1,
                    "code": line_stripped,
                    "explanation": f"Declares the main contract '{contract_name}'. " + 
                                 (f"Inherits from: {inheritance}" if inheritance else "No inheritance."),
                    "importance": "critical"
                })
            
            elif line_stripped.startswith('uint') or line_stripped.startswith('mapping') or line_stripped.startswith('address') or line_stripped.startswith('string') or line_stripped.startswith('bool'):
                if 'constant' in line_stripped or 'immutable' in line_stripped:
                    if current_section != "constants":
                        if current_section:
                            explanations[-1]["line_end"] = i
                        current_section = "constants"
                        explanations.append({
                            "section": "Constants & Immutable Variables",
                            "line_start": i + 1,
                            "code": line_stripped,
                            "explanation": "Defines constants and immutable variables. These save gas as they're stored in the contract bytecode.",
                            "importance": "medium"
                        })
                    else:
                        explanations[-1]["code"] += f"\n{line_stripped}"
                else:
                    if current_section != "state_variables":
                        if current_section:
                            explanations[-1]["line_end"] = i
                        current_section = "state_variables"
                        explanations.append({
                            "section": "State Variables",
                            "line_start": i + 1,
                            "code": line_stripped,
                            "explanation": "Defines the contract's storage variables. These persist between function calls and cost gas to modify.",
                            "importance": "high"
                        })
                    else:
                        explanations[-1]["code"] += f"\n{line_stripped}"
            
            elif line_stripped.startswith('event '):
                if current_section != "events":
                    if current_section:
                        explanations[-1]["line_end"] = i
                    current_section = "events"
                    event_name = line_stripped.split()[1].split('(')[0]
                    explanations.append({
                        "section": "Events",
                        "line_start": i + 1,
                        "code": line_stripped,
                        "explanation": f"Defines event '{event_name}'. Events allow external applications to listen for contract activity.",
                        "importance": "medium"
                    })
                else:
                    explanations[-1]["code"] += f"\n{line_stripped}"
            
            elif line_stripped.startswith('modifier '):
                if current_section:
                    explanations[-1]["line_end"] = i
                modifier_name = line_stripped.split()[1].split('(')[0]
                
                # Find the end of the modifier
                modifier_end = i
                brace_count = 0
                for j in range(i, len(lines)):
                    brace_count += lines[j].count('{') - lines[j].count('}')
                    if brace_count == 0 and '{' in ''.join(lines[i:j+1]):
                        modifier_end = j
                        break
                
                modifier_code = '\n'.join(lines[i:modifier_end+1])
                
                explanations.append({
                    "section": f"Modifier: {modifier_name}",
                    "line_start": i + 1,
                    "line_end": modifier_end + 1,
                    "code": modifier_code,
                    "explanation": f"Modifier '{modifier_name}' adds reusable checks to functions. The '_' symbol indicates where the function code executes.",
                    "importance": "high"
                })
                current_section = None
            
            elif line_stripped.startswith('constructor'):
                if current_section:
                    explanations[-1]["line_end"] = i
                
                # Find the end of the constructor
                constructor_end = i
                brace_count = 0
                for j in range(i, len(lines)):
                    brace_count += lines[j].count('{') - lines[j].count('}')
                    if brace_count == 0 and '{' in ''.join(lines[i:j+1]):
                        constructor_end = j
                        break
                
                constructor_code = '\n'.join(lines[i:constructor_end+1])
                
                explanations.append({
                    "section": "Constructor",
                    "line_start": i + 1,
                    "line_end": constructor_end + 1,
                    "code": constructor_code,
                    "explanation": "The constructor runs once when the contract is deployed. It initializes the contract's state.",
                    "importance": "critical"
                })
                current_section = None
            
            elif line_stripped.startswith('function '):
                if current_section:
                    explanations[-1]["line_end"] = i
                
                func_name = line_stripped.split()[1].split('(')[0]
                
                # Find the end of the function
                function_end = i
                brace_count = 0
                for j in range(i, len(lines)):
                    brace_count += lines[j].count('{') - lines[j].count('}')
                    if brace_count == 0 and '{' in ''.join(lines[i:j+1]):
                        function_end = j
                        break
                
                function_code = '\n'.join(lines[i:function_end+1])
                
                # Analyze function type
                visibility = 'internal'
                if 'public' in line_stripped:
                    visibility = 'public'
                elif 'external' in line_stripped:
                    visibility = 'external'
                elif 'private' in line_stripped:
                    visibility = 'private'
                
                state_mutability = 'nonpayable'
                if 'view' in line_stripped:
                    state_mutability = 'view'
                elif 'pure' in line_stripped:
                    state_mutability = 'pure'
                elif 'payable' in line_stripped:
                    state_mutability = 'payable'
                
                explanation_text = f"Function '{func_name}' with {visibility} visibility and {state_mutability} state mutability."
                
                if state_mutability == 'view':
                    explanation_text += " This function only reads data and doesn't modify state."
                elif state_mutability == 'pure':
                    explanation_text += " This function doesn't read or modify state."
                elif state_mutability == 'payable':
                    explanation_text += " This function can receive Ether."
                else:
                    explanation_text += " This function can modify contract state."
                
                explanations.append({
                    "section": f"Function: {func_name}",
                    "line_start": i + 1,
                    "line_end": function_end + 1,
                    "code": function_code,
                    "explanation": explanation_text,
                    "importance": "high",
                    "visibility": visibility,
                    "state_mutability": state_mutability
                })
                current_section = None
        
        # Close the last section
        if current_section and explanations:
            explanations[-1]["line_end"] = len(lines)
        
        # Generate summary
        summary = {
            "total_sections": len(explanations),
            "functions": len([e for e in explanations if e["section"].startswith("Function:")]),
            "modifiers": len([e for e in explanations if e["section"].startswith("Modifier:")]),
            "events": len([e for e in explanations if e["section"] == "Events"]),
            "state_variables": 1 if any(e["section"] == "State Variables" for e in explanations) else 0,
            "complexity": "low" if len(explanations) < 5 else "medium" if len(explanations) < 10 else "high"
        }
        
        return {
            "status": "success",
            "data": {
                "explanations": explanations,
                "summary": summary,
                "total_lines": len(lines),
                "complexity_score": min(100, len(explanations) * 8)
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Code explanation failed: {str(e)}"}
