# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

import re
import json
import os
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime


def format_solidity_code(contract_code: str) -> Dict[str, Any]:
    """Apply consistent formatting and styling to Solidity code."""
    try:
        lines = contract_code.split('\n')
        formatted_lines = []
        indent_level = 0
        in_comment_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                formatted_lines.append('')
                continue
            
            # Handle comment blocks
            if '/*' in stripped and '*/' not in stripped:
                in_comment_block = True
            elif '*/' in stripped:
                in_comment_block = False
            
            # Handle single-line comments and comment blocks
            if stripped.startswith('//') or stripped.startswith('*') or in_comment_block:
                formatted_lines.append('    ' * indent_level + stripped)
                continue
            
            # Handle SPDX and pragma
            if stripped.startswith('//') and 'SPDX' in stripped:
                formatted_lines.append(stripped)
                continue
            
            if stripped.startswith('pragma'):
                formatted_lines.append(stripped)
                continue
            
            # Handle imports
            if stripped.startswith('import'):
                formatted_lines.append(stripped)
                continue
            
            # Decrease indent for closing braces
            if stripped.startswith('}'):
                indent_level = max(0, indent_level - 1)
            
            # Apply indentation
            formatted_line = '    ' * indent_level + stripped
            
            # Handle spacing around operators
            formatted_line = re.sub(r'(\w)\s*=\s*(\w)', r'\1 = \2', formatted_line)
            formatted_line = re.sub(r'(\w)\s*\+\s*(\w)', r'\1 + \2', formatted_line)
            formatted_line = re.sub(r'(\w)\s*-\s*(\w)', r'\1 - \2', formatted_line)
            formatted_line = re.sub(r'(\w)\s*\*\s*(\w)', r'\1 * \2', formatted_line)
            formatted_line = re.sub(r'(\w)\s*/\s*(\w)', r'\1 / \2', formatted_line)
            
            # Handle spacing around commas
            formatted_line = re.sub(r',(\w)', r', \1', formatted_line)
            
            # Handle spacing in function declarations
            formatted_line = re.sub(r'function\s+(\w+)\s*\(', r'function \1(', formatted_line)
            
            formatted_lines.append(formatted_line)
            
            # Increase indent for opening braces
            if stripped.endswith('{'):
                indent_level += 1
        
        # Remove extra empty lines
        cleaned_lines = []
        prev_empty = False
        for line in formatted_lines:
            if line.strip() == '':
                if not prev_empty:
                    cleaned_lines.append(line)
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False
        
        # Add proper spacing between sections
        final_lines = []
        for i, line in enumerate(cleaned_lines):
            final_lines.append(line)
            
            # Add extra line after imports
            if line.strip().startswith('import') and i + 1 < len(cleaned_lines):
                next_line = cleaned_lines[i + 1].strip()
                if next_line and not next_line.startswith('import'):
                    final_lines.append('')
            
            # Add extra line after contract declaration
            if 'contract ' in line and '{' in line:
                final_lines.append('')
        
        formatted_code = '\n'.join(final_lines)
        
        return {
            "status": "success",
            "data": {
                "formatted_code": formatted_code,
                "original_lines": len(lines),
                "formatted_lines": len(final_lines),
                "formatting_applied": [
                    "Consistent indentation",
                    "Proper spacing around operators",
                    "Clean comment formatting",
                    "Section separation",
                    "Removed extra empty lines"
                ]
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Code formatting failed: {str(e)}"}


def get_contract_metrics(contract_code: str) -> Dict[str, Any]:
    """Calculate contract size, complexity metrics, and other statistics."""
    try:
        lines = contract_code.split('\n')
        
        # Basic metrics
        total_lines = len(lines)
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('//')])
        comment_lines = len([line for line in lines if line.strip().startswith('//')])
        empty_lines = total_lines - code_lines - comment_lines
        
        # Extract contract elements
        functions = []
        modifiers = []
        events = []
        state_variables = []
        imports = []
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith('import'):
                imports.append(stripped)
            elif stripped.startswith('function ') and ('private' not in stripped and 'internal' not in stripped):
                func_match = re.search(r'function\s+(\w+)', stripped)
                if func_match:
                    functions.append(func_match.group(1))
            elif stripped.startswith('modifier '):
                mod_match = re.search(r'modifier\s+(\w+)', stripped)
                if mod_match:
                    modifiers.append(mod_match.group(1))
            elif stripped.startswith('event '):
                event_match = re.search(r'event\s+(\w+)', stripped)
                if event_match:
                    events.append(event_match.group(1))
            elif any(stripped.startswith(t) for t in ['uint', 'int', 'address', 'string', 'bool', 'bytes', 'mapping']):
                if not any(keyword in stripped for keyword in ['function', 'modifier', 'event', 'constructor']):
                    var_match = re.search(r'(public|private|internal)?\s*\w+\s+(\w+)', stripped)
                    if var_match:
                        state_variables.append(var_match.group(2))
        
        # Complexity calculations
        cyclomatic_complexity = 1  # Base complexity
        complexity_keywords = ['if', 'else', 'for', 'while', 'do', 'switch', 'case', '&&', '||', '?']
        
        for line in lines:
            for keyword in complexity_keywords:
                cyclomatic_complexity += line.count(keyword)
        
        # Security features detection
        security_features = {
            "reentrancy_guard": "ReentrancyGuard" in contract_code,
            "access_control": any(keyword in contract_code for keyword in ["onlyOwner", "AccessControl", "Ownable"]),
            "pausable": "Pausable" in contract_code,
            "safe_math": "SafeMath" in contract_code or "pragma solidity ^0.8" in contract_code,
            "emergency_stop": "emergencyStop" in contract_code,
            "rate_limiting": "dailyLimit" in contract_code or "rateLimit" in contract_code
        }
        
        # Gas optimization features
        gas_optimizations = {
            "immutable_variables": "immutable" in contract_code,
            "constant_variables": "constant" in contract_code,
            "packed_structs": "struct" in contract_code and "packed" in contract_code,
            "external_functions": "external" in contract_code,
            "view_functions": "view" in contract_code,
            "pure_functions": "pure" in contract_code
        }
        
        # Calculate complexity score
        complexity_score = min(100, (len(functions) * 5) + (cyclomatic_complexity * 2) + (len(state_variables) * 3))
        
        # Calculate maintainability score
        maintainability_score = max(0, 100 - complexity_score + (comment_lines * 2))
        
        # Calculate security score
        security_score = sum(security_features.values()) * 15
        
        return {
            "status": "success",
            "data": {
                "line_metrics": {
                    "total_lines": total_lines,
                    "code_lines": code_lines,
                    "comment_lines": comment_lines,
                    "empty_lines": empty_lines,
                    "comment_ratio": round(comment_lines / max(total_lines, 1) * 100, 2)
                },
                "contract_elements": {
                    "functions": len(functions),
                    "function_names": functions,
                    "modifiers": len(modifiers),
                    "modifier_names": modifiers,
                    "events": len(events),
                    "event_names": events,
                    "state_variables": len(state_variables),
                    "variable_names": state_variables,
                    "imports": len(imports)
                },
                "complexity_metrics": {
                    "cyclomatic_complexity": cyclomatic_complexity,
                    "complexity_score": complexity_score,
                    "complexity_rating": "low" if complexity_score < 30 else "medium" if complexity_score < 60 else "high"
                },
                "security_features": security_features,
                "gas_optimizations": gas_optimizations,
                "quality_scores": {
                    "maintainability": maintainability_score,
                    "security": security_score,
                    "overall": round((maintainability_score + security_score) / 2, 2)
                }
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Metrics calculation failed: {str(e)}"}


def suggest_improvements(contract_code: str) -> Dict[str, Any]:
    """Analyze code for optimization opportunities and suggest better patterns."""
    try:
        suggestions = []
        gas_optimizations = []
        security_improvements = []
        code_quality = []
        
        lines = contract_code.split('\n')
        
        # Gas optimization suggestions
        if "uint256" in contract_code and "uint8" not in contract_code:
            gas_optimizations.append({
                "type": "gas_optimization",
                "category": "data_types",
                "suggestion": "Consider using smaller uint types (uint8, uint16, uint32) for variables that don't need the full range of uint256",
                "impact": "medium",
                "estimated_savings": "2000-5000 gas per variable"
            })
        
        if contract_code.count("mapping(") > 3:
            gas_optimizations.append({
                "type": "gas_optimization",
                "category": "storage",
                "suggestion": "Multiple mappings detected. Consider using structs to pack related data together",
                "impact": "high",
                "estimated_savings": "20000+ gas per transaction"
            })
        
        if "string" in contract_code and "bytes32" not in contract_code:
            gas_optimizations.append({
                "type": "gas_optimization",
                "category": "data_types",
                "suggestion": "For fixed-length strings, consider using bytes32 instead of string to save gas",
                "impact": "medium",
                "estimated_savings": "1000-3000 gas per operation"
            })
        
        # Check for loop optimizations
        for i, line in enumerate(lines):
            if "for (" in line:
                if "i++" in line:
                    gas_optimizations.append({
                        "type": "gas_optimization",
                        "category": "loops",
                        "line": i + 1,
                        "suggestion": "Use ++i instead of i++ in loops to save gas",
                        "impact": "low",
                        "estimated_savings": "5 gas per iteration"
                    })
                
                if ".length" in line:
                    gas_optimizations.append({
                        "type": "gas_optimization",
                        "category": "loops",
                        "line": i + 1,
                        "suggestion": "Cache array length before loop to avoid repeated SLOAD operations",
                        "impact": "medium",
                        "estimated_savings": "100+ gas per iteration"
                    })
        
        # Security improvement suggestions
        if "require(" not in contract_code and "assert(" not in contract_code:
            security_improvements.append({
                "type": "security",
                "category": "input_validation",
                "suggestion": "Add require() statements for input validation to prevent invalid states",
                "severity": "high"
            })
        
        if "onlyOwner" not in contract_code and "AccessControl" not in contract_code:
            if any(func in contract_code for func in ["mint", "burn", "pause", "withdraw"]):
                security_improvements.append({
                    "type": "security",
                    "category": "access_control",
                    "suggestion": "Add access control to sensitive functions like mint, burn, pause, withdraw",
                    "severity": "critical"
                })
        
        if "ReentrancyGuard" not in contract_code and ".call(" in contract_code:
            security_improvements.append({
                "type": "security",
                "category": "reentrancy",
                "suggestion": "Add ReentrancyGuard to functions that make external calls",
                "severity": "high"
            })
        
        # Check for missing events
        function_lines = [line for line in lines if "function " in line and "public" in line]
        event_lines = [line for line in lines if "event " in line]
        
        if len(function_lines) > len(event_lines):
            security_improvements.append({
                "type": "security",
                "category": "transparency",
                "suggestion": "Add events to important state-changing functions for better transparency and monitoring",
                "severity": "medium"
            })
        
        # Code quality suggestions
        if contract_code.count("// TODO") > 0:
            code_quality.append({
                "type": "code_quality",
                "category": "completeness",
                "suggestion": "Remove TODO comments and implement missing functionality",
                "priority": "high"
            })
        
        long_functions = []
        current_function = None
        function_length = 0
        
        for line in lines:
            if "function " in line:
                if current_function and function_length > 50:
                    long_functions.append(current_function)
                current_function = line.strip()
                function_length = 0
            elif current_function:
                function_length += 1
        
        if long_functions:
            code_quality.append({
                "type": "code_quality",
                "category": "function_length",
                "suggestion": f"Consider breaking down long functions: {', '.join(long_functions[:3])}",
                "priority": "medium"
            })
        
        # Check for missing documentation
        natspec_count = contract_code.count("///")
        function_count = contract_code.count("function ")
        
        if natspec_count < function_count:
            code_quality.append({
                "type": "code_quality",
                "category": "documentation",
                "suggestion": "Add NatSpec documentation (///) to functions for better code documentation",
                "priority": "medium"
            })
        
        # Advanced pattern suggestions
        advanced_patterns = []
        
        if "factory" not in contract_code.lower() and contract_code.count("contract ") > 1:
            advanced_patterns.append({
                "type": "architecture",
                "category": "design_pattern",
                "suggestion": "Consider using Factory pattern for deploying multiple similar contracts",
                "benefit": "Reduced deployment costs and better code organization"
            })
        
        if "proxy" not in contract_code.lower() and len(contract_code) > 10000:
            advanced_patterns.append({
                "type": "architecture",
                "category": "upgradeability",
                "suggestion": "Consider implementing proxy pattern for contract upgradeability",
                "benefit": "Allow future upgrades while preserving state and address"
            })
        
        # Compile all suggestions
        all_suggestions = gas_optimizations + security_improvements + code_quality + advanced_patterns
        
        # Priority scoring
        priority_scores = {
            "critical": 100,
            "high": 80,
            "medium": 60,
            "low": 40
        }
        
        total_score = 0
        suggestion_count = len(all_suggestions)
        
        for suggestion in all_suggestions:
            severity = suggestion.get("severity", suggestion.get("priority", suggestion.get("impact", "medium")))
            total_score += priority_scores.get(severity, 50)
        
        improvement_score = max(0, 100 - (total_score // max(suggestion_count, 1)))
        
        return {
            "status": "success",
            "data": {
                "gas_optimizations": gas_optimizations,
                "security_improvements": security_improvements,
                "code_quality": code_quality,
                "advanced_patterns": advanced_patterns,
                "summary": {
                    "total_suggestions": len(all_suggestions),
                    "gas_optimizations": len(gas_optimizations),
                    "security_issues": len(security_improvements),
                    "code_quality_issues": len(code_quality),
                    "improvement_score": improvement_score,
                    "priority_breakdown": {
                        "critical": len([s for s in all_suggestions if s.get("severity") == "critical" or s.get("priority") == "critical"]),
                        "high": len([s for s in all_suggestions if s.get("severity") == "high" or s.get("priority") == "high"]),
                        "medium": len([s for s in all_suggestions if s.get("severity") == "medium" or s.get("priority") == "medium"]),
                        "low": len([s for s in all_suggestions if s.get("severity") == "low" or s.get("priority") == "low"])
                    }
                }
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Suggestion analysis failed: {str(e)}"}


# =============================================================================
# INTEGRATION FUNCTIONS
# =============================================================================

def save_contract_project(contract_data_json: str, project_name: str) -> Dict[str, Any]:
    """Save generated contract with associated files and create project structure."""
    try:
        # Parse contract data JSON string to dict
        import json
        contract_data = json.loads(contract_data_json) if isinstance(contract_data_json, str) else contract_data_json
        
        # Create project directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = Path(f"{project_name}_{timestamp}")
        project_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        contracts_dir = project_dir / "contracts"
        tests_dir = project_dir / "tests"
        docs_dir = project_dir / "docs"
        scripts_dir = project_dir / "scripts"
        
        for directory in [contracts_dir, tests_dir, docs_dir, scripts_dir]:
            directory.mkdir(exist_ok=True)
        
        # Save main contract
        contract_file = contracts_dir / f"{project_name}.sol"
        with open(contract_file, 'w') as f:
            f.write(contract_data.get('contract_code', ''))
        
        # Save ABI if available
        if 'abi' in contract_data:
            abi_file = contracts_dir / f"{project_name}_abi.json"
            with open(abi_file, 'w') as f:
                json.dump(contract_data['abi'], f, indent=2)
        
        # Save bytecode if available
        if 'bytecode' in contract_data:
            bytecode_file = contracts_dir / f"{project_name}_bytecode.txt"
            with open(bytecode_file, 'w') as f:
                f.write(contract_data['bytecode'])
        
        # Generate package.json
        package_json = {
            "name": project_name.lower().replace(" ", "-"),
            "version": "1.0.0",
            "description": f"Smart contract project: {project_name}",
            "main": "index.js",
            "scripts": {
                "compile": "npx hardhat compile",
                "test": "npx hardhat test",
                "deploy": "npx hardhat run scripts/deploy.js"
            },
            "devDependencies": {
                "@nomiclabs/hardhat-ethers": "^2.2.3",
                "@nomiclabs/hardhat-waffle": "^2.0.6",
                "chai": "^4.3.10",
                "ethereum-waffle": "^4.0.10",
                "ethers": "^6.9.0",
                "hardhat": "^2.19.0"
            },
            "dependencies": {
                "@openzeppelin/contracts": "^5.0.0"
            }
        }
        
        with open(project_dir / "package.json", 'w') as f:
            json.dump(package_json, f, indent=2)
        
        # Generate hardhat.config.js
        hardhat_config = '''require("@nomiclabs/hardhat-waffle");
require("@nomiclabs/hardhat-ethers");

// This is a sample Hardhat task
task("accounts", "Prints the list of accounts", async (taskArgs, hre) => {
  const accounts = await hre.ethers.getSigners();
  for (const account of accounts) {
    console.log(account.address);
  }
});

module.exports = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    hardhat: {
      chainId: 1337
    },
    localhost: {
      url: "http://127.0.0.1:8545"
    },
    goerli: {
      url: process.env.GOERLI_URL || "",
      accounts: process.env.PRIVATE_KEY !== undefined ? [process.env.PRIVATE_KEY] : []
    },
    mainnet: {
      url: process.env.MAINNET_URL || "",
      accounts: process.env.PRIVATE_KEY !== undefined ? [process.env.PRIVATE_KEY] : []
    }
  },
  gasReporter: {
    enabled: process.env.REPORT_GAS !== undefined,
    currency: "USD"
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY
  }
};
'''
        
        with open(project_dir / "hardhat.config.js", 'w') as f:
            f.write(hardhat_config)
        
        # Generate deployment script
        deploy_script = f'''const hre = require("hardhat");

async function main() {{
  const [deployer] = await hre.ethers.getSigners();
  
  console.log("Deploying contracts with the account:", deployer.address);
  console.log("Account balance:", (await deployer.getBalance()).toString());
  
  const {project_name} = await hre.ethers.getContractFactory("{project_name}");
  const contract = await {project_name}.deploy(
    // Add constructor parameters here
  );
  
  await contract.deployed();
  
  console.log("{project_name} deployed to:", contract.address);
  
  // Verify contract on Etherscan (if on mainnet/testnet)
  if (hre.network.name !== "hardhat" && hre.network.name !== "localhost") {{
    console.log("Waiting for block confirmations...");
    await contract.deployTransaction.wait(6);
    await hre.run("verify:verify", {{
      address: contract.address,
      constructorArguments: [
        // Add constructor arguments here
      ],
    }});
  }}
}}

main()
  .then(() => process.exit(0))
  .catch((error) => {{
    console.error(error);
    process.exit(1);
  }});
'''
        
        with open(scripts_dir / "deploy.js", 'w') as f:
            f.write(deploy_script)
        
        # Generate basic test file
        test_content = f'''const {{ expect }} = require("chai");
const {{ ethers }} = require("hardhat");

describe("{project_name}", function () {{
  let contract;
  let owner;
  let addr1;
  let addr2;
  
  beforeEach(async function () {{
    [owner, addr1, addr2] = await ethers.getSigners();
    
    const {project_name} = await ethers.getContractFactory("{project_name}");
    contract = await {project_name}.deploy(
      // Add constructor parameters
    );
    await contract.deployed();
  }});
  
  describe("Deployment", function () {{
    it("Should deploy successfully", async function () {{
      expect(contract.address).to.not.equal(0);
    }});
    
    // Add more deployment tests
  }});
  
  // Add more test suites for different functions
}});
'''
        
        with open(tests_dir / f"{project_name}.test.js", 'w') as f:
            f.write(test_content)
        
        # Generate README
        readme_content = f'''# {project_name}

## Description
This smart contract project was generated using the Smart Contract Generator.

## Setup
1. Install dependencies:
   ```bash
   npm install
   ```

2. Compile contracts:
   ```bash
   npx hardhat compile
   ```

3. Run tests:
   ```bash
   npx hardhat test
   ```

4. Deploy to local network:
   ```bash
   npx hardhat node
   npx hardhat run scripts/deploy.js --network localhost
   ```

## Project Structure
- `contracts/` - Smart contract source files
- `tests/` - Test files
- `scripts/` - Deployment and utility scripts
- `docs/` - Documentation

## Configuration
Create a `.env` file with the following variables:
```
PRIVATE_KEY=your_private_key
GOERLI_URL=your_goerli_rpc_url
MAINNET_URL=your_mainnet_rpc_url
ETHERSCAN_API_KEY=your_etherscan_api_key
```

## License
MIT
'''
        
        with open(project_dir / "README.md", 'w') as f:
            f.write(readme_content)
        
        # Generate .gitignore
        gitignore_content = '''node_modules/
.env
coverage/
coverage.json
typechain/
typechain-types/

# Hardhat files
cache/
artifacts/

# IDE
.vscode/
.idea/
'''
        
        with open(project_dir / ".gitignore", 'w') as f:
            f.write(gitignore_content)
        
        # Create environment template
        env_template = '''# Copy this file to .env and fill in your values
PRIVATE_KEY=
GOERLI_URL=
MAINNET_URL=
ETHERSCAN_API_KEY=
REPORT_GAS=false
'''
        
        with open(project_dir / ".env.example", 'w') as f:
            f.write(env_template)
        
        return {
            "status": "success",
            "data": {
                "project_directory": str(project_dir.absolute()),
                "files_created": [
                    f"contracts/{project_name}.sol",
                    f"contracts/{project_name}_abi.json",
                    f"tests/{project_name}.test.js",
                    "scripts/deploy.js",
                    "package.json",
                    "hardhat.config.js",
                    "README.md",
                    ".gitignore",
                    ".env.example"
                ],
                "next_steps": [
                    "Navigate to project directory",
                    "Run 'npm install' to install dependencies", 
                    "Copy .env.example to .env and configure",
                    "Run 'npx hardhat compile' to compile contracts",
                    "Run 'npx hardhat test' to run tests"
                ]
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Project creation failed: {str(e)}"}


def export_to_framework(contract_code: str, framework: str, contract_name: str = "CustomContract") -> Dict[str, Any]:
    """Export contract to different development frameworks (Hardhat, Truffle, Brownie)."""
    try:
        if framework.lower() not in ["hardhat", "truffle", "brownie"]:
            return {"status": "error", "error_message": f"Unsupported framework: {framework}. Supported: hardhat, truffle, brownie"}
        
        export_data = {
            "framework": framework,
            "contract_code": contract_code,
            "config_files": {},
            "scripts": {},
            "package_files": {}
        }
        
        if framework.lower() == "hardhat":
            # Hardhat configuration
            export_data["config_files"]["hardhat.config.js"] = '''require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.19",
  networks: {
    hardhat: {},
    goerli: {
      url: process.env.GOERLI_URL,
      accounts: [process.env.PRIVATE_KEY]
    }
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY
  }
};'''
            
            export_data["package_files"]["package.json"] = {
                "devDependencies": {
                    "@nomicfoundation/hardhat-toolbox": "^4.0.0",
                    "hardhat": "^2.19.0"
                }
            }
            
        elif framework.lower() == "truffle":
            # Truffle configuration
            export_data["config_files"]["truffle-config.js"] = '''module.exports = {
  networks: {
    development: {
      host: "127.0.0.1",
      port: 8545,
      network_id: "*"
    },
    goerli: {
      provider: () => new HDWalletProvider(
        process.env.PRIVATE_KEY,
        process.env.GOERLI_URL
      ),
      network_id: 5,
      gas: 5500000
    }
  },
  compilers: {
    solc: {
      version: "0.8.19"
    }
  }
};'''
            
            export_data["package_files"]["package.json"] = {
                "devDependencies": {
                    "truffle": "^5.11.5",
                    "@truffle/hdwallet-provider": "^2.1.15"
                }
            }
            
            # Migration script
            export_data["scripts"]["migrations/2_deploy_contracts.js"] = f'''const {contract_name} = artifacts.require("{contract_name}");

module.exports = function (deployer) {{
  deployer.deploy({contract_name});
}};'''
            
        elif framework.lower() == "brownie":
            # Brownie configuration
            export_data["config_files"]["brownie-config.yaml"] = '''dependencies:
  - OpenZeppelin/openzeppelin-contracts@4.9.0

compiler:
  solc:
    version: 0.8.19
    optimizer:
      enabled: true
      runs: 200

networks:
  default: development
  development:
    host: http://127.0.0.1:8545
  goerli:
    host: https://goerli.infura.io/v3/$WEB3_INFURA_PROJECT_ID
    gas_limit: 6721975
    gas_buffer: 1.1
    gas_price: 20000000000'''
            
            # Python deployment script
            export_data["scripts"]["deploy.py"] = f'''from brownie import {contract_name}, accounts

def main():
    account = accounts[0]
    contract = {contract_name}.deploy(
        # Add constructor parameters
        {{"from": account}}
    )
    print(f"{contract_name} deployed to: {{contract.address}}")
    return contract'''
            
            export_data["package_files"]["requirements.txt"] = '''eth-brownie>=1.20.0
pytest>=7.0.0'''
        
        return {
            "status": "success",
            "data": export_data
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Framework export failed: {str(e)}"}


# =============================================================================
# ERROR HANDLING AND VALIDATION
# =============================================================================

def handle_compilation_errors(errors_json: str) -> Dict[str, Any]:
    """Parse compiler errors and suggest fixes."""
    try:
        # Parse errors JSON string to list
        import json
        errors = json.loads(errors_json) if isinstance(errors_json, str) else errors_json
        
        parsed_errors = []
        suggestions = []
        
        for error in errors:
            error_info = {
                "original_error": error,
                "error_type": "unknown",
                "line_number": None,
                "suggestion": "Check the error message for details"
            }
            
            # Parse line numbers
            line_match = re.search(r':(\d+):', error)
            if line_match:
                error_info["line_number"] = int(line_match.group(1))
            
            # Categorize common errors
            if "ParserError" in error:
                error_info["error_type"] = "syntax_error"
                if "Expected" in error:
                    error_info["suggestion"] = "Check syntax - missing semicolon, bracket, or parenthesis"
                elif "Unexpected" in error:
                    error_info["suggestion"] = "Remove unexpected character or check syntax"
                    
            elif "TypeError" in error:
                error_info["error_type"] = "type_error"
                if "not found" in error:
                    error_info["suggestion"] = "Check if variable/function is declared and spelled correctly"
                elif "not compatible" in error:
                    error_info["suggestion"] = "Check data types - ensure compatible types for assignment/comparison"
                elif "not callable" in error:
                    error_info["suggestion"] = "Check if you're trying to call a variable as a function"
                    
            elif "DeclarationError" in error:
                error_info["error_type"] = "declaration_error"
                if "already declared" in error:
                    error_info["suggestion"] = "Variable or function name already exists - use a different name"
                elif "not declared" in error:
                    error_info["suggestion"] = "Declare the variable or import the contract/library"
                    
            elif "CompilerError" in error:
                error_info["error_type"] = "compiler_error"
                error_info["suggestion"] = "Internal compiler error - try different solidity version"
                
            elif "Warning" in error:
                error_info["error_type"] = "warning"
                if "unused" in error:
                    error_info["suggestion"] = "Remove unused variables/imports or prefix with underscore"
                elif "deprecated" in error:
                    error_info["suggestion"] = "Update to use newer syntax or functions"
            
            parsed_errors.append(error_info)
        
        # Generate general suggestions
        error_types = [e["error_type"] for e in parsed_errors]
        
        if "syntax_error" in error_types:
            suggestions.append("Review code syntax carefully - check for missing semicolons, brackets, and parentheses")
        
        if "type_error" in error_types:
            suggestions.append("Verify all variable types and function signatures match their usage")
        
        if "declaration_error" in error_types:
            suggestions.append("Ensure all variables and functions are properly declared before use")
        
        # Error severity classification
        severity_count = {
            "critical": len([e for e in parsed_errors if e["error_type"] in ["syntax_error", "compiler_error"]]),
            "high": len([e for e in parsed_errors if e["error_type"] in ["type_error", "declaration_error"]]),
            "medium": len([e for e in parsed_errors if e["error_type"] == "warning"]),
            "low": 0
        }
        
        return {
            "status": "success",
            "data": {
                "parsed_errors": parsed_errors,
                "total_errors": len(parsed_errors),
                "error_types": list(set(error_types)),
                "severity_count": severity_count,
                "general_suggestions": suggestions,
                "fixable_errors": len([e for e in parsed_errors if e["error_type"] != "compiler_error"])
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Error parsing failed: {str(e)}"}


def validate_user_input(user_description: str) -> Dict[str, Any]:
    """Check if request is feasible and clear, ask clarifying questions when needed."""
    try:
        description = user_description.strip().lower()
        
        # Check for basic requirements
        validation_results = {
            "is_feasible": True,
            "clarity_score": 0,
            "missing_info": [],
            "suggestions": [],
            "estimated_complexity": "unknown",
            "recommended_contract_type": None
        }
        
        # Contract type detection
        contract_indicators = {
            "erc20": ["token", "erc20", "fungible", "currency", "coin"],
            "erc721": ["nft", "erc721", "non-fungible", "collectible", "unique"],
            "erc1155": ["erc1155", "multi-token", "batch", "gaming"],
            "dao": ["dao", "governance", "voting", "proposal", "community"],
            "dex": ["dex", "exchange", "swap", "liquidity", "trading"],
            "staking": ["staking", "stake", "reward", "yield", "farming"],
            "marketplace": ["marketplace", "auction", "buy", "sell", "listing"],
            "multisig": ["multisig", "multi-signature", "multiple owners", "threshold"]
        }
        
        detected_types = []
        for contract_type, keywords in contract_indicators.items():
            if any(keyword in description for keyword in keywords):
                detected_types.append(contract_type)
        
        if detected_types:
            validation_results["recommended_contract_type"] = detected_types[0]
            validation_results["clarity_score"] += 30
        else:
            validation_results["missing_info"].append("contract_type")
            validation_results["suggestions"].append("Please specify what type of smart contract you want (e.g., token, NFT, DAO, DEX)")
        
        # Check for specific requirements
        requirement_keywords = {
            "name": ["name", "called", "title"],
            "symbol": ["symbol", "ticker", "abbreviation"],
            "supply": ["supply", "amount", "quantity", "total"],
            "features": ["feature", "function", "capability", "ability"],
            "access": ["owner", "admin", "permission", "access", "control"],
            "security": ["secure", "safe", "protection", "guard"]
        }
        
        found_requirements = []
        for req, keywords in requirement_keywords.items():
            if any(keyword in description for keyword in keywords):
                found_requirements.append(req)
                validation_results["clarity_score"] += 10
        
        # Check description length and detail
        word_count = len(description.split())
        if word_count < 5:
            validation_results["suggestions"].append("Please provide more details about your requirements")
            validation_results["clarity_score"] -= 20
        elif word_count > 100:
            validation_results["clarity_score"] += 20
        else:
            validation_results["clarity_score"] += 10
        
        # Estimate complexity
        complexity_indicators = {
            "simple": ["simple", "basic", "minimal", "standard"],
            "complex": ["complex", "advanced", "custom", "sophisticated", "enterprise"],
            "features": ["upgrade", "proxy", "oracle", "multi", "batch", "governance"]
        }
        
        complexity_score = 1
        if any(keyword in description for keyword in complexity_indicators["complex"]):
            complexity_score += 2
        if any(keyword in description for keyword in complexity_indicators["features"]):
            complexity_score += 1
        if len(found_requirements) > 4:
            complexity_score += 1
        
        if complexity_score <= 2:
            validation_results["estimated_complexity"] = "simple"
        elif complexity_score <= 4:
            validation_results["estimated_complexity"] = "moderate"
        else:
            validation_results["estimated_complexity"] = "complex"
        
        # Generate clarifying questions
        clarifying_questions = []
        
        if "contract_type" in validation_results["missing_info"]:
            clarifying_questions.append("What type of smart contract do you want to create? (e.g., ERC-20 token, NFT, DAO)")
        
        if "name" not in found_requirements and validation_results["recommended_contract_type"]:
            clarifying_questions.append("What would you like to name your contract/token?")
        
        if validation_results["recommended_contract_type"] == "erc20" and "symbol" not in found_requirements:
            clarifying_questions.append("What symbol should your token have? (e.g., BTC, ETH)")
        
        if validation_results["recommended_contract_type"] == "erc20" and "supply" not in found_requirements:
            clarifying_questions.append("What should be the total supply of your token?")
        
        if "access" not in found_requirements:
            clarifying_questions.append("Do you need access control? (e.g., only owner can mint, admin roles)")
        
        if "security" not in found_requirements and validation_results["estimated_complexity"] != "simple":
            clarifying_questions.append("What security features do you need? (e.g., pausable, reentrancy protection)")
        
        # Final feasibility check
        if len(validation_results["missing_info"]) > 3 or validation_results["clarity_score"] < 20:
            validation_results["is_feasible"] = False
            validation_results["suggestions"].append("Please provide more specific details about your requirements")
        
        return {
            "status": "success",
            "data": {
                **validation_results,
                "clarifying_questions": clarifying_questions,
                "detected_contract_types": detected_types,
                "found_requirements": found_requirements,
                "word_count": word_count,
                "needs_clarification": len(clarifying_questions) > 0
            }
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Input validation failed: {str(e)}"}
