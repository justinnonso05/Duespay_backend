<div align="center">

# 💳 DuesPay

### *Revolutionizing Campus Dues Collection*

**A modern, intelligent platform that transforms how campus organizations collect, manage, and verify payments**

[![Django](https://img.shields.io/badge/Django-5.2. 5-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![DRF](https://img.shields.io/badge/DRF-3.16. 0-red.svg)](https://www.django-rest-framework.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Live Demo](https://duespay.app) • [API Docs](https://duespay.onrender.com/docs) • [Report Bug](https://github.com/justinnonso05/Duespay_backend/issues)

</div>

---

## 🎯 The Problem

Campus organizations (halls, departments, faculties) face **massive challenges** with dues collection:

- ❌ Manual payment tracking leads to errors and disputes
- ❌ No standardized system across different organizations  
- ❌ Time-consuming verification of bank transfer receipts
- ❌ Poor financial transparency and accountability
- ❌ Students lose receipts and can't prove payment
- ❌ No easy way to track who paid what, when

**DuesPay solves all of these problems and more.**

---

## 💡 Our Solution

DuesPay is a **comprehensive digital dues management platform** that brings automation, transparency, and intelligence to campus payment systems. 

### 🌟 Key Features

#### For Organizations (Halls, Departments, Faculties)
- 🏢 **Multi-Organization Support** - Each organization gets a custom subdomain and dashboard
- 📊 **Real-time Analytics** - Track payments, pending dues, and financial reports
- 🎨 **Customizable Branding** - Custom logos, themes, and colors
- 📅 **Session Management** - Organize dues by academic sessions/years
- 💰 **Flexible Payment Items** - Create compulsory or optional fees for specific levels
- ✅ **Smart Verification** - AI-powered proof of payment validation using Google Gemini
- 📧 **Automated Notifications** - Email alerts for new transactions
- 🧾 **Digital Receipts** - Auto-generated receipts with unique IDs

#### For Students (Payers)
- 💳 **Multiple Payment Methods** - Card payments and bank transfers via Paystack
- 📱 **Instant Payment Confirmation** - Real-time payment status updates
- 🎫 **Digital Receipt Storage** - Access receipts anytime via unique URLs
- 🔍 **Payment History** - View all past transactions
- ⚡ **Quick Payer Registration** - One-time setup with matric number verification
- 📲 **Mobile-Friendly** - Responsive design for all devices

---

## 🏗️ Architecture & Tech Stack

### Backend Framework
```
Django 5.2.5 + Django REST Framework 3.16.0
```

### Core Technologies

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Language** | Python 3.11+ | Backend development |
| **Framework** | Django 5.2.5 | Web framework |
| **API** | Django REST Framework | RESTful API |
| **Database** | PostgreSQL | Production database |
| **File Storage** | Cloudinary | Media & document hosting |
| **Payments** | Paystack API | Payment processing |
| **AI** | Google Gemini API | Receipt verification |
| **Email** | Brevo (Sendinblue) | Transactional emails |
| **Auth** | JWT (SimpleJWT) | Token-based authentication |
| **Deployment** | Render/Fly.io | Cloud hosting |
| **Admin UI** | Django Unfold | Modern admin interface |

### System Architecture

```
┌─────────────────┐
│   Frontend      │ (React/Next.js - separate repo)
│  (duespay.app)  │
└────────┬────────┘
         │ HTTPS/REST API
         ▼
┌─────────────────────────────────────┐
│     Django REST Framework API       │
│  ┌─────────┬──────────┬──────────┐ │
│  │  Auth   │ Business │   File   │ │
│  │  Layer  │  Logic   │ Upload   │ │
│  └─────────┴──────────┴──────────┘ │
└──────────┬──────────────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌──────────┐ ┌──────────────┐
│PostgreSQL│ │  Cloudinary  │
│ Database │ │ Media Storage│
└──────────┘ └──────────────┘
     │
     ▼
┌────────────────────────┐
│  External Services     │
│ • Paystack (Payments)  │
│ • Gemini AI (OCR)      │
│ • Brevo (Emails)       │
└────────────────────────┘
```

---

## 📦 Project Structure

```
Duespay_backend/
├── main/                    # Core authentication & user management
│   ├── models.py           # AdminUser model
│   ├── authentication.py   # JWT authentication
│   └── views.py            # Auth endpoints
│
├── association/            # Organization management
│   ├── models. py          # Association, Session, Notification
│   ├── views.py           # CRUD operations
│   └── signals.py         # Auto-creation logic
│
├── payers/                # Student/payer management  
│   ├── models. py         # Payer model with session tracking
│   ├── services.py       # Payer validation logic
│   └── views.py          # Payer endpoints
│
├── payments/             # Payment configuration
│   ├── models. py        # PaymentItem, BankAccount
│   ├── bankServices.py  # Bank verification service
│   └── views. py         # Payment item management
│
├── transactions/         # Transaction processing
│   ├── models. py        # Transaction, TransactionReceipt
│   ├── services.py      # AI verification service (Gemini)
│   ├── paystackServices.py  # Payment gateway integration
│   ├── signals.py       # Auto receipt generation
│   └── views. py         # Transaction endpoints
│
├── utils/               # Shared utilities
│   └── utils.py        # File validation helpers
│
├── config/             # Django configuration
│   ├── settings/      
│   │   ├── base.py    # Base settings
│   │   ├── dev.py     # Development config
│   │   └── prod.py    # Production config
│   └── urls.py        # URL routing
│
├── requirements. txt    # Python dependencies
├── Dockerfile         # Docker configuration
├── fly.toml          # Fly.io deployment config
└── manage.py         # Django management script
```

---

## 🚀 Key Innovations

### 1. **AI-Powered Receipt Verification** 🤖
Using Google Gemini AI, DuesPay can automatically extract and verify information from payment receipts: 
- Beneficiary name validation
- Amount verification
- Date extraction
- OCR for images and PDFs

### 2. **Session-Based Multi-Tenancy** 🏫
Organizations can manage multiple academic sessions simultaneously:
- Each session has isolated payers and transactions
- Support for session switching
- Historical data preservation

### 3. **Smart Payer Management** 👥
- Automatic duplicate detection
- Session-scoped uniqueness constraints
- Update existing payers vs.  create new ones
- Level-based payment categorization

### 4. **Automated Receipt Generation** 🧾
- Auto-incrementing receipt numbers per organization
- PDF-ready formatted receipts
- Email delivery system
- Permanent URL access via receipt ID

### 5. **Flexible Payment Configuration** ⚙️
- Compulsory vs. optional payment items
- Level-specific requirements (100-600 levels)
- Dynamic pricing per session
- Active/inactive status control

---

## 🔐 Security Features

- ✅ JWT-based authentication with token refresh
- ✅ Role-based access control (Admin vs. Payer)
- ✅ CSRF protection
- ✅ CORS configuration
- ✅ Environment-based settings (dev/prod)
- ✅ Secure webhook signature validation (Paystack)
- ✅ PostgreSQL with SSL in production
- ✅ Cloudinary secure file uploads

---

## 📊 Database Models

### Core Entities

1. **AdminUser** - Organization administrators
2. **Association** - Campus organizations (halls, departments, faculties)
3. **Session** - Academic sessions/years
4. **Payer** - Students making payments
5. **PaymentItem** - Configurable fee items
6. **Transaction** - Payment records
7. **TransactionReceipt** - Digital receipts
8. **ReceiverBankAccount** - Organization bank details
9. **Notification** - In-app notifications

### Relationship Diagram
```
AdminUser 1──1 Association
Association 1──* Session
Association 1──* Payer
Association 1──* PaymentItem
Association 1──* Transaction
Association 1──1 ReceiverBankAccount

Payer 1──* Transaction
Transaction 1──1 TransactionReceipt
Transaction *──* PaymentItem
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Cloudinary account
- Paystack account
- Google Cloud account (for Gemini API)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/justinnonso05/Duespay_backend.git
cd Duespay_backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment setup**
```bash
cp .env.example .env
# Edit . env with your credentials
```

5. **Database setup**
```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **Run development server**
```bash
./run. sh  # or python manage.py runserver
```

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost: 5432/duespay

# Django
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=your-secret-key

# Cloudinary
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Paystack
PAYSTACK_SECRET=your-secret-key
PAYSTACK_PUBLIC=your-public-key
PAYSTACK_WEBHOOK_SECRET=your-webhook-secret

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Email (Brevo)
BREVO_API_KEY=your-brevo-api-key

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-client-id

# URLs
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
```

---

## 🧪 API Endpoints

### Authentication
```
POST   /api/auth/register/          # Register new admin user
POST   /api/auth/login/             # Login
POST   /api/auth/token/refresh/     # Refresh JWT token
POST   /api/auth/google/            # Google OAuth login
```

### Associations
```
GET    /api/associations/profiles/              # List associations
POST   /api/associations/profiles/              # Create association
GET    /api/associations/get-association/{id}/  # Get by short name
PATCH  /api/associations/profiles/{id}/         # Update association
```

### Sessions
```
GET    /api/associations/sessions/          # List sessions
POST   /api/associations/sessions/          # Create session
PATCH  /api/associations/sessions/{id}/     # Update/activate session
```

### Payers
```
GET    /api/payers/                  # List payers
POST   /api/payers/check/            # Check or create payer
GET    /api/payers/{id}/             # Get payer details
```

### Payment Items
```
GET    /api/payments/payment-items/           # List items
POST   /api/payments/payment-items/           # Create item
PATCH  /api/payments/payment-items/{id}/      # Update item
```

### Transactions
```
GET    /api/transactions/                        # List transactions
POST   /api/transactions/payment/initiate/       # Initialize payment
GET    /api/transactions/payment/status/{ref}/   # Check payment status
POST   /api/transactions/webhook/                # Paystack webhook
GET    /api/transactions/receipts/{id}/          # Get receipt
```

### Full API Documentation
- **Swagger UI**:  `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`

---

## 🎨 Admin Dashboard

DuesPay includes a beautiful, modern admin interface powered by **Django Unfold**: 

- 📊 Visual analytics and charts
- 🔍 Advanced filtering and search
- 📱 Responsive design
- 🎨 Customizable color schemes
- 📥 CSV export functionality

Access at: `http://localhost:8000/admin/`

---

## 🌍 Deployment

### Using Fly.io (Recommended)
```bash
fly launch
fly deploy
```

### Using Render
1. Connect your GitHub repo
2. Set environment variables
3. Deploy from the dashboard

### Using Docker
```bash
docker build -t duespay-backend .
docker run -p 8000:8000 duespay-backend
```

---

## 📈 Scalability & Performance

- ✅ **Database Optimization**: Proper indexing on foreign keys and unique fields
- ✅ **Caching**: Bank list caching (24-hour TTL)
- ✅ **Pagination**: All list endpoints support pagination (default 7 items)
- ✅ **Query Optimization**: `select_related()` and `prefetch_related()` usage
- ✅ **Async Support**: Built on ASGI-ready Django 5.2
- ✅ **CDN Integration**: Cloudinary for global media delivery
- ✅ **Database Connection Pooling**: `conn_max_age=600`

---

## 🧩 Future Enhancements

- [ ] 📱 Mobile app (React Native)
- [ ] 📊 Advanced analytics dashboard with charts
- [ ] 💬 In-app chat support
- [ ] 🔔 Push notifications
- [ ] 📄 Bulk import/export (CSV/Excel)
- [ ] 🎯 Payment reminders and deadline tracking
- [ ] 🏆 Leaderboards for early payers
- [ ] 🔐 Two-factor authentication
- [ ] 📧 SMS notifications (Twilio integration)
- [ ] 💱 Multi-currency support
- [ ] 🤝 Integration with university portals

---

## 👥 Team

- **Developer**: [@justinnonso05](https://github.com/justinnonso05)

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact & Support

- **Email**: jcmailer. 1@gmail.com
- **Website**: [duespay.app](https://duespay.app)
- **Documentation**: [API Docs](https://duespay.onrender.com/api/schema/swagger-ui/)
- **Issues**: [GitHub Issues](https://github.com/justinnonso05/Duespay_backend/issues)

---

## 🌟 Acknowledgments

- Django & DRF community
- Paystack for payment infrastructure
- Google Gemini for AI capabilities
- Cloudinary for media storage
- All contributors and testers

---

<div align="center">

### ⭐ Star this repo if you find it useful!

**Built with ❤️ for the campus community**

[⬆ Back to Top](#-duespay)

</div>
