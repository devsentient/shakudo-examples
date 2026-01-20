# AgentOS | n8n Orchestrator Dashboard

AgentOS is a specialized management interface designed for high-density n8n environments. It allows you to monitor, search, and control hundreds of AI agents from a single, high-performance dashboard.



## 🚀 Key Features

* **Global Search**: Instantly filter through 100+ workflows by name or ID.
* **One-Click Controls**: High-contrast buttons for triggering and deploying agents.
* **Live Heartbeat**: Visual pulsing indicators for active "Deployed" workflows.
* **Secure API Proxy**: Next.js server-side routes protect your n8n API keys and bypass OIDC gateways.
* **Auto-Pagination**: Seamlessly handles large workflow databases via cursor-based fetching.

## 🛠️ Tech Stack

| Technology | Usage |
| :--- | :--- |
| **Next.js 16** | Full-stack React framework (App Router) |
| **Tailwind CSS** | Utility-first styling with high-contrast theme |
| **Lucide Icons** | Professional iconography for system status |
| **Prettier/ESLint** | Code quality and standard formatting |

## ⚙️ Configuration

The application requires two environment variables to communicate with your cluster. Create a `.env.local` file:

```text
N8N_BASE_URL=http://your-n8n-internal-service/api/v1
N8N_API_KEY=your-n8n-public-api-key