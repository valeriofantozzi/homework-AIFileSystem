# ⚙️ config/ — Environment & Model Configuration Hub 🗝️

Welcome to the **config** directory!  
This is the control center for all environment, API key, and model provider configuration in your AI agent system.  
Here, you’ll find everything you need to securely manage environments, LLM providers, and role-based model selection. 🔐🌍

---

## What’s Inside? 📦

- **models.yaml**: 🧠 Central model/provider/role configuration (YAML, with env var support)
- **env_loader.py**: 🔄 Loads environment variables and API keys for any deployment
- **manage_env.py**: 🖥️ CLI for setting up, validating, and listing environments
- **exceptions.py**: 🚨 Custom exceptions for robust error handling
- **model_config.py**: 🏗️ Core logic for model/provider selection and validation
- **env/**: 📁 Templates for all supported environments (local, dev, test, prod)
- **.env.local**: 🗝️ Example local environment file (never commit real keys!)
- **ENV_SETUP.md**: 📖 Step-by-step guide for environment setup and security

---

## Key Features & Principles ✨

- **High Cohesion**: Each module has a single, clear responsibility (env loading, model config, CLI, etc.)
- **Low Coupling**: No hardcoded secrets or provider logic in the app code
- **Security First**: API keys are always externalized—never in code or VCS!
- **Role-Based Model Selection**: Assign different models/providers to each agent role
- **Environment Templates**: Easy switching between dev, test, and prod
- **CLI Tools**: Setup, validate, and list environments with a single command

---

## Folder Structure 🗂️

| File/Folder       | Purpose                                                     |
| ----------------- | ----------------------------------------------------------- |
| `models.yaml`     | 🧠 Central model/provider/role configuration                |
| `env_loader.py`   | 🔄 Loads environment variables and API keys                 |
| `manage_env.py`   | 🖥️ CLI for environment setup and validation                 |
| `exceptions.py`   | 🚨 Custom exceptions for config errors                      |
| `model_config.py` | 🏗️ Model/provider selection and validation logic            |
| `env/`            | 📁 Environment template files                               |
| `.env.local`      | 🗝️ Example local environment file (never commit real keys!) |
| `ENV_SETUP.md`    | 📖 Environment setup and security guide                     |

---

## How to Use 🚀

1. **Install dependencies:**  
   `poetry install`

2. **Set up your environment:**  
   `python config/manage_env.py setup local`  
   or for dev:  
   `python config/manage_env.py setup development`

3. **Add your API keys:**  
   Edit `.env.local` or `.env.development` as needed (see ENV_SETUP.md for details)

4. **Switch environments in code:**

   ```python
   from config import set_environment
   set_environment('development')
   ```

5. **Check your config:**  
   `python config/manage_env.py validate local`

---

## Security Best Practices 🔒

- **Never commit real .env files or API keys to git**
- **Use different keys for dev, test, and prod**
- **Rotate keys regularly and monitor usage**
- **Templates in `env/` help you stay secure by default**

---

## Why This Matters 💡

- **Separation of Concerns**: No secrets or environment logic in your app code
- **Easy to Extend**: Add new providers, roles, or environments in one place
- **Safe by Design**: Security and best practices are built in

---

**Configure once. Run anywhere. Stay secure!** 🛡️⚙️
