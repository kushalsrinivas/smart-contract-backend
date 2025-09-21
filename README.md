# Smart Contract Generator — AI-Powered dApp Development Assistant

An advanced AI agent built with Google ADK that interprets user requirements and generates secure, efficient Solidity smart contracts with comprehensive tooling and documentation.

## 🌟 Features

### 🏗️ **Contract Generation**

- **Multiple Contract Types**: ERC-20 tokens, ERC-721 NFTs, DAOs, DEX, staking contracts, multi-signature wallets
- **Template System**: Pre-built, security-audited templates using OpenZeppelin standards
- **Custom Parameters**: Automatic customization based on user requirements
- **Advanced Features**: Custom functions, modifiers, events, and state variables

### 🔒 **Security & Best Practices**

- **Security Analysis**: Automated vulnerability detection and security scoring
- **OpenZeppelin Integration**: Industry-standard security implementations
- **Access Control**: Ownable, role-based, and custom permission systems
- **Security Features**: Reentrancy guards, pause functionality, emergency stops

### ⚙️ **Compilation & Analysis**

- **Solidity Compilation**: Integrated py-solc-x compiler with error handling
- **Gas Analysis**: Detailed gas usage estimation and optimization suggestions
- **Code Metrics**: Complexity analysis, quality scoring, and maintainability assessment
- **Vulnerability Scanning**: Automated detection of common smart contract vulnerabilities

### 🧪 **Testing & Deployment**

- **Test Generation**: Automated test suite creation with comprehensive coverage
- **Deployment Simulation**: Test network deployment with cost estimation
- **Framework Support**: Export to Hardhat, Truffle, or Brownie frameworks
- **CI/CD Ready**: Complete project structure with configuration files

### 📚 **Documentation & Education**

- **Auto-Documentation**: NatSpec comments and comprehensive documentation generation
- **Code Explanation**: Line-by-line breakdown of generated contracts
- **Best Practices**: Educational insights and optimization recommendations
- **Project Packaging**: Complete development environment setup

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Google ADK CLI installed
- Gemini API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd adk-agent-server-ready-template

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
export GOOGLE_API_KEY="your_gemini_api_key"
export ALLOWED_ORIGINS="http://localhost:3000"  # Optional: for CORS
```

### Running the Server

```bash
# Start the FastAPI server
python server.py

# Server will be available at http://localhost:8080
```

## 📝 Usage Examples

### 1. Generate an ERC-20 Token

```bash
curl -X POST http://localhost:8080/run_sse \
  -H 'Content-Type: application/json' \
  -d '{
    "app_name": "agent",
    "user_id": "demo",
    "session_id": "s1",
    "new_message": {
      "role": "user",
      "parts": [{"text": "Create an ERC-20 token called SuperCoin with symbol SUPER, total supply of 1 million tokens, and only owner can mint new tokens."}]
    },
    "streaming": false
  }'
```

### 2. Create an NFT Collection

```bash
curl -X POST http://localhost:8080/run_sse \
  -H 'Content-Type: application/json' \
  -d '{
    "app_name": "agent",
    "user_id": "demo",
    "session_id": "s1",
    "new_message": {
      "role": "user",
      "parts": [{"text": "I want to create an NFT collection called CryptoArt with 10,000 unique pieces, public minting at 0.05 ETH each, and royalties for the creator."}]
    },
    "streaming": false
  }'
```

### 3. Build a Multi-Signature Wallet

```bash
curl -X POST http://localhost:8080/run_sse \
  -H 'Content-Type: application/json' \
  -d '{
    "app_name": "agent",
    "user_id": "demo",
    "session_id": "s1",
    "new_message": {
      "role": "user",
      "parts": [{"text": "Create a multi-signature wallet that requires 3 out of 5 signatures to execute transactions, with daily spending limits."}]
    },
    "streaming": false
  }'
```

## 🛠️ Available Tools

### **Template Management**

- `get_available_templates()` - List all supported contract types
- `select_contract_template(contract_type)` - Get template for specific type

### **Code Generation**

- `generate_contract_code(template, parameters)` - Fill template with custom parameters
- `add_custom_functions(contract_code, functions)` - Add custom business logic
- `implement_access_control(contract_code, access_rules)` - Add permission systems

### **Security & Validation**

- `add_security_features(contract_code, security_level)` - Add security measures
- `validate_contract_structure(contract_code)` - Check for vulnerabilities

### **Compilation & Analysis**

- `compile_contract(contract_code)` - Compile Solidity code
- `analyze_gas_usage(bytecode, abi)` - Estimate gas costs and optimizations

### **Testing & Deployment**

- `generate_test_suite(contract_code, abi)` - Create comprehensive tests
- `simulate_contract_deployment(contract_code, network)` - Deploy to test networks

### **Documentation & Utilities**

- `generate_contract_documentation(contract_code)` - Create documentation
- `explain_generated_code(contract_code)` - Explain code functionality
- `format_solidity_code(contract_code)` - Apply consistent formatting
- `get_contract_metrics(contract_code)` - Calculate complexity metrics
- `suggest_improvements(contract_code)` - Optimization recommendations

### **Project Management**

- `save_contract_project(contract_data, project_name)` - Save complete project
- `export_to_framework(contract_code, framework)` - Export to dev frameworks
- `handle_compilation_errors(errors)` - Parse and suggest fixes
- `validate_user_input(user_description)` - Validate requirements

## 🏗️ Project Structure

```
smart-contract-generator/
├── agent/
│   ├── __init__.py
│   ├── agent.py              # Main agent with core functions
│   ├── contract_utils.py     # Compilation, testing, documentation
│   └── contract_helpers.py   # Utilities, integration, error handling
├── server.py                 # FastAPI server with CORS
├── requirements.txt          # Dependencies including blockchain libraries
└── README.md                # This file
```

## 🧪 Testing

The agent includes comprehensive testing capabilities:

```bash
# Example: Test the agent locally
python -c "
from agent.agent import get_available_templates, select_contract_template
print(get_available_templates())
result = select_contract_template('erc20')
print(result['data']['template_code'][:200])
"
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key

# Optional
ALLOWED_ORIGINS=http://localhost:3000,https://yourapp.com
ADK_SERVE_WEB=true
PORT=8080
HOST=0.0.0.0
RELOAD=1
```

### Supported Networks

- **Local Development**: Ganache, Hardhat Network
- **Testnets**: Goerli, Sepolia, Mumbai
- **Mainnets**: Ethereum, Polygon (for final deployment)

## 🎯 Use Cases

### **DeFi Applications**

- Token creation and management
- Staking and farming contracts
- Decentralized exchanges
- Yield farming protocols

### **NFT Projects**

- Art collections and marketplaces
- Gaming assets and utilities
- Membership and access tokens
- Royalty and revenue sharing

### **DAO & Governance**

- Voting mechanisms
- Treasury management
- Proposal systems
- Community governance

### **Enterprise Solutions**

- Multi-signature wallets
- Access control systems
- Asset tokenization
- Supply chain tracking

## 🔒 Security Considerations

The agent prioritizes security through:

- **OpenZeppelin Standards**: Using battle-tested, audited contracts
- **Vulnerability Detection**: Automated scanning for common issues
- **Security Levels**: Configurable security features (basic/medium/high/maximum)
- **Best Practices**: Following Ethereum development standards
- **Code Review**: Generated contracts include security recommendations

## 📖 Documentation

Each generated contract includes:

- **NatSpec Comments**: Standard Ethereum documentation
- **Function Descriptions**: Clear explanations of all functionality
- **Security Notes**: Important security considerations
- **Usage Examples**: How to interact with the contract
- **Deployment Guide**: Step-by-step deployment instructions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Update documentation
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

For issues and questions:

- Create an issue in the repository
- Check the documentation for common solutions
- Review the generated contract comments for guidance

---

**⚠️ Disclaimer**: Generated smart contracts should be thoroughly reviewed and tested before deployment to mainnet. Consider professional auditing for production applications.
# smart-contract-backend
