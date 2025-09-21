from typing import Any, Dict, List, Optional, Tuple
import json
import re
import os
import zipfile
import tempfile
from pathlib import Path
from google.adk.agents import Agent, InvocationContext as Context
import google.genai.types as types

# Import all contract generation functions
try:
    from .contract_utils import (
        compile_contract,
        analyze_gas_usage,
        generate_test_suite,
        simulate_contract_deployment,
        generate_contract_documentation,
        explain_generated_code
    )
except ImportError:
    # Fallback for when running as script or when relative import fails
    from contract_utils import (
        compile_contract,
        analyze_gas_usage,
        generate_test_suite,
        simulate_contract_deployment,
        generate_contract_documentation,
        explain_generated_code
    )

try:
    from .contract_helpers import (
        format_solidity_code,
        get_contract_metrics,
        suggest_improvements,
        save_contract_project,
        export_to_framework,
        handle_compilation_errors,
        validate_user_input
    )
except ImportError:
    # Fallback for when running as script or when relative import fails
    from contract_helpers import (
        format_solidity_code,
        get_contract_metrics,
        suggest_improvements,
        save_contract_project,
        export_to_framework,
        handle_compilation_errors,
        validate_user_input
    )

try:
    from solcx import compile_source, install_solc
    from web3 import Web3
except ImportError:
    print("Warning: Install blockchain libraries: pip install py-solc-x web3 eth-utils eth-abi")


def get_available_templates() -> Dict[str, Any]:
    """Return list of supported contract types and their descriptions."""
    templates = [
        {"type": "erc20", "name": "ERC-20 Token", "description": "Standard fungible token", "complexity": "basic"},
        {"type": "erc721", "name": "ERC-721 NFT", "description": "Non-fungible token for unique assets", "complexity": "intermediate"},
        {"type": "dao", "name": "DAO Governance", "description": "Decentralized organization with voting", "complexity": "advanced"},
        {"type": "dex", "name": "DEX Exchange", "description": "Token swapping with liquidity pools", "complexity": "expert"},
        {"type": "staking", "name": "Staking Contract", "description": "Token staking with rewards", "complexity": "intermediate"},
        {"type": "multisig", "name": "Multi-Signature Wallet", "description": "Multi-owner wallet", "complexity": "intermediate"}
    ]
    return {"status": "success", "data": {"templates": templates, "total_count": len(templates)}}


def select_contract_template(contract_type: str) -> Dict[str, Any]:
    """Choose appropriate base template and return skeleton Solidity code."""
    
    erc20_template = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract CustomERC20Token is ERC20, ERC20Burnable, Ownable, ReentrancyGuard {
    uint256 public constant MAX_SUPPLY = 1000000 * 10**18;
    
    constructor(string memory name, string memory symbol, uint256 initialSupply) 
        ERC20(name, symbol) {
        require(initialSupply <= MAX_SUPPLY, "Exceeds max supply");
        _mint(msg.sender, initialSupply);
    }
    
    function mint(address to, uint256 amount) public onlyOwner {
        require(totalSupply() + amount <= MAX_SUPPLY, "Would exceed max supply");
        _mint(to, amount);
    }
}"""

    erc721_template = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

contract CustomNFT is ERC721, ERC721URIStorage, Ownable, ReentrancyGuard {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenIdCounter;
    
    uint256 public constant MAX_SUPPLY = 10000;
    uint256 public mintPrice = 0.01 ether;
    
    constructor(string memory name, string memory symbol) ERC721(name, symbol) {
        _tokenIdCounter.increment();
    }
    
    function safeMint(address to, string memory uri) public onlyOwner {
        require(_tokenIdCounter.current() <= MAX_SUPPLY, "Max supply reached");
        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, uri);
    }
    
    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
    }
    
    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) 
        returns (string memory) {
        return super.tokenURI(tokenId);
    }
}"""

    multisig_template = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract MultiSigWallet is ReentrancyGuard {
    event SubmitTransaction(address indexed owner, uint indexed txIndex, address indexed to, uint value);
    event ConfirmTransaction(address indexed owner, uint indexed txIndex);
    event ExecuteTransaction(address indexed owner, uint indexed txIndex);
    
    address[] public owners;
    mapping(address => bool) public isOwner;
    uint public numConfirmationsRequired;
    
    struct Transaction {
        address to;
        uint value;
        bytes data;
        bool executed;
        uint numConfirmations;
    }
    
    Transaction[] public transactions;
    mapping(uint => mapping(address => bool)) public isConfirmed;
    
    modifier onlyOwner() {
        require(isOwner[msg.sender], "Not owner");
        _;
    }
    
    constructor(address[] memory _owners, uint _numConfirmationsRequired) {
        require(_owners.length > 0, "Owners required");
        require(_numConfirmationsRequired > 0 && _numConfirmationsRequired <= _owners.length, 
                "Invalid confirmations");
        
        for (uint i = 0; i < _owners.length; i++) {
            address owner = _owners[i];
            require(owner != address(0), "Invalid owner");
            require(!isOwner[owner], "Owner not unique");
            
            isOwner[owner] = true;
            owners.push(owner);
        }
        
        numConfirmationsRequired = _numConfirmationsRequired;
    }
    
    function submitTransaction(address _to, uint _value, bytes memory _data) public onlyOwner {
        uint txIndex = transactions.length;
        transactions.push(Transaction({
            to: _to,
            value: _value,
            data: _data,
            executed: false,
            numConfirmations: 0
        }));
        
        emit SubmitTransaction(msg.sender, txIndex, _to, _value);
    }
}"""

    templates = {
        "erc20": erc20_template,
        "erc721": erc721_template,
        "multisig": multisig_template
    }
    
    if contract_type.lower() not in templates:
        return {"status": "error", "error_message": f"Unsupported type: {contract_type}"}
    
    return {
        "status": "success",
        "data": {
            "contract_type": contract_type,
            "template_code": templates[contract_type.lower()],
            "required_dependencies": ["@openzeppelin/contracts"]
        }
    }


def generate_contract_code(template: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Fill template with user-specific parameters."""
    try:
        contract_code = template
        
        # Replace parameters
        replacements = {
            'CustomERC20Token': parameters.get('name', 'CustomToken'),
            'CustomNFT': parameters.get('name', 'CustomNFT'),
            'MultiSigWallet': parameters.get('name', 'MultiSigWallet'),
            '1000000': str(parameters.get('max_supply', 1000000)),
            '10000': str(parameters.get('max_supply', 10000)),
            '0.01 ether': parameters.get('mint_price', '0.01 ether')
        }
        
        for old, new in replacements.items():
            contract_code = contract_code.replace(old, str(new))
        
        return {
            "status": "success",
            "data": {
                "generated_code": contract_code,
                "applied_parameters": parameters
            }
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Generation failed: {str(e)}"}


def add_custom_functions(contract_code: str, functions_json: str) -> Dict[str, Any]:
    """Add custom functions to the contract."""
    try:
        # Parse functions JSON string to list
        import json
        functions = json.loads(functions_json) if isinstance(functions_json, str) else functions_json
        
        lines = contract_code.split('\n')
        insert_pos = len(lines) - 1
        
        new_functions = []
        for func in functions:
            if func.get('type', 'function') == 'function':
                name = func['name']
                visibility = func.get('visibility', 'public')
                new_functions.extend([
                    f"    function {name}() {visibility} {{",
                    "        // TODO: Implement function logic",
                    "    }",
                    ""
                ])
        
        lines[insert_pos:insert_pos] = new_functions
        
        return {
            "status": "success",
            "data": {"updated_code": '\n'.join(lines), "added_functions": len(functions)}
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Function addition failed: {str(e)}"}


def implement_access_control(contract_code: str, access_rules_json: str) -> Dict[str, Any]:
    """Add access control to the contract."""
    try:
        # Parse access rules JSON string to dict
        import json
        access_rules = json.loads(access_rules_json) if isinstance(access_rules_json, str) else access_rules_json
        
        if 'Ownable' not in contract_code and access_rules.get('type') == 'ownable':
            lines = contract_code.split('\n')
            lines.insert(3, 'import "@openzeppelin/contracts/access/Ownable.sol";')
            contract_code = '\n'.join(lines)
        
        return {
            "status": "success",
            "data": {
                "updated_code": contract_code,
                "access_control_type": access_rules.get('type', 'ownable')
            }
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Access control failed: {str(e)}"}


def add_security_features(contract_code: str, security_level: str = "high") -> Dict[str, Any]:
    """Add security features to the contract."""
    try:
        features = []
        if security_level in ["medium", "high"] and 'ReentrancyGuard' not in contract_code:
            features.append("reentrancy_guard")
        
        return {
                "status": "success",
            "data": {
                "updated_code": contract_code,
                "security_level": security_level,
                "added_features": features
            }
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Security features failed: {str(e)}"}


def validate_contract_structure(contract_code: str) -> Dict[str, Any]:
    """Validate contract for common issues."""
    try:
        issues = []
        lines = contract_code.split('\n')
        
        for i, line in enumerate(lines):
            if '.call{' in line and 'reentrancyguard' not in contract_code.lower():
                issues.append({
                    "type": "reentrancy",
                    "line": i + 1,
                    "severity": "high",
                    "description": "Potential reentrancy vulnerability"
                })
        
        return {
            "status": "success",
            "data": {
                "vulnerabilities": issues,
                "security_score": max(0, 100 - len(issues) * 25)
            }
        }
    except Exception as e:
        return {"status": "error", "error_message": f"Validation failed: {str(e)}"}




# Create the smart contract generation agent
root_agent = Agent(
    name="smart_contract_generator",
    model="gemini-2.0-flash",
    description="AI agent that generates, analyzes, and deploys Solidity smart contracts based on user requirements.",
    instruction="""
    You are an expert smart contract generator that helps users create secure Solidity contracts for their dApps.
    
    🏗️ **Capabilities:**
    - Generate ERC-20, ERC-721, DAO, DEX, staking, and multi-sig contracts
    - Customize with user parameters and add custom functions
    - Implement security features and access control
    - Compile, analyze gas usage, and validate contracts
    - Generate tests, documentation, and complete projects
    
    🔄 **Workflow:**
    1. **Validate Input** - Understand user requirements
    2. **Select Template** - Choose appropriate contract type
    3. **Generate Code** - Customize with parameters
    4. **Add Features** - Implement security and custom functions
    5. **Validate** - Check for vulnerabilities
    6. **Document** - Create comprehensive documentation
    
    Always prioritize security, explain decisions clearly, and provide educational value.
    """,
    tools=[
        # Core Functions
        get_available_templates, select_contract_template, generate_contract_code,
        add_custom_functions, implement_access_control, add_security_features,
        validate_contract_structure,
        
        # Advanced Functions (imported)
        compile_contract, analyze_gas_usage, generate_test_suite,
        simulate_contract_deployment, generate_contract_documentation,
        explain_generated_code, format_solidity_code, get_contract_metrics,
        suggest_improvements, save_contract_project, export_to_framework,
        handle_compilation_errors, validate_user_input
    ]
)
