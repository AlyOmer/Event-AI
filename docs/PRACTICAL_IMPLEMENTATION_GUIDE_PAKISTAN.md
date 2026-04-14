# Agentic Event Orchestrator - Practical Implementation Guide (Pakistan Edition)

**Version**: 2.0 - Revised for Pakistan Market  
**Date**: February 2026  
**Project**: AI-Powered Event Planning System  
**Authors**: M Omair (BSAI-FA22-033), Ali Umer (BSAI-FA22-040)  
**Supervisor**: M. Javed

---

## ⚠️ IMPORTANT UPDATES - Addressing Your Concerns

### 1. Is Kubernetes Necessary? **NO!**

**Short Answer**: Kubernetes is **NOT necessary** for initial development and launch. Start simple!

**Recommended Deployment Path**:

```
Stage 1 (MVP - Month 1-4): Simple Deployment
├── Single VPS/Server (Hostinger, DigitalOcean, or local Pakistani hosting)
├── Docker Compose for all services
├── Cost: PKR 5,000-15,000/month
└── Can handle 100-500 events/month

Stage 2 (Growth - Month 5-8): Managed Services
├── Multiple VPS instances
├── Managed PostgreSQL (DigitalOcean, AWS RDS)
├── Cost: PKR 30,000-50,000/month
└── Can handle 1,000-5,000 events/month

Stage 3 (Scale - Year 2): Kubernetes (Optional)
├── Only when you have 10,000+ events/month
├── Cost: PKR 100,000+/month
└── Can handle unlimited events
```

**We'll focus on Stage 1 & 2 in this guide!**

### 2. Currency: Using PKR (Pakistani Rupees)

All costs updated to PKR! Current exchange rate: 1 USD ≈ PKR 280

### 3. Vendor Registration Flow

**YES! Vendors MUST register.** Here's how it works:

```
Vendor Onboarding Flow:
├── 1. Vendor Creates Account (Email + Password)
├── 2. Vendor Fills Profile
│   ├── Business Name
│   ├── Category (Catering, Venue, Decoration, etc.)
│   ├── Service Areas (Cities they operate in)
│   ├── Pricing Range
│   ├── Portfolio Images
│   └── Availability Calendar
├── 3. Admin Verification (Manual Review)
│   ├── Checks business legitimacy
│   ├── Verifies contact info
│   └── Approves or rejects
├── 4. Vendor Goes Live
│   └── Appears in search results
└── 5. Vendor Manages Bookings
    ├── Receives booking requests
    ├── Accepts/Rejects
    └── Updates availability
```

### 4. Scalability Path

**YES! Very Scalable** - But in stages:

```
Scalability Journey:

Week 1-4 (Development):
└── Your laptop → 1 user (you testing)

Month 1-3 (Beta):
└── 1 Server → 50-100 concurrent users → 500 events/month

Month 4-6 (Launch):
└── 1-2 Servers → 200-500 concurrent users → 2,000 events/month

Month 7-12 (Growth):
└── 3-5 Servers → 1,000+ concurrent users → 10,000 events/month

Year 2+ (Scale):
└── Cloud Auto-scaling → 10,000+ concurrent users → Unlimited events
```

---

## Updated Implementation Plan: Start Simple, Scale Smart

## Phase 1: Simple Start (No Kubernetes!)

### Architecture - Version 1.0 (Simple)

```
┌─────────────────────────────────────────────────────────┐
│         SINGLE SERVER (VPS - PKR 5,000-10,000/mo)       │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  NGINX (Reverse Proxy + Load Balancer)          │  │
│  │  Port 80/443                                     │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│       ┌──────────────────┴──────────────────┐          │
│       ▼                                      ▼          │
│  ┌─────────────┐                    ┌─────────────┐    │
│  │  Frontend   │                    │   Backend   │    │
│  │  (Next.js)  │                    │   (FastAPI) │    │
│  │  Port 3000  │                    │   Port 8000 │    │
│  └─────────────┘                    └─────────────┘    │
│                                              │          │
│       ┌──────────────────────────────────────┘          │
│       │                                                  │
│       ▼                                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Docker Compose Services:                       │   │
│  │  ├── PostgreSQL (Database)                      │   │
│  │  ├── Redis (Cache)                              │   │
│  │  ├── RabbitMQ (Message Queue) - Optional       │   │
│  │  └── All Agent Services (Python containers)    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Docker Compose Setup (Simple Deployment)

```yaml
# docker-compose.yml - Production-ready, No Kubernetes!

version: '3.8'

services:
  # Frontend (Next.js)
  frontend:
    build: ./frontend/user-app
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped

  # Backend API (FastAPI)
  backend:
    build: ./services/event-planner-agent
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://eventplanner:password@postgres:5432/eventplanner_db
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SENDGRID_API_KEY=${SENDGRID_API_KEY}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  # Database
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: eventplanner
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: eventplanner_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    restart: unless-stopped

  # Cache
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # Nginx (Reverse Proxy)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  default:
    driver: bridge
```

### Deployment on Single VPS

```bash
# 1. Choose a hosting provider in Pakistan or nearby
# Options:
# - Local: Hostinger Pakistan, Truehost, Cloudways
# - International: DigitalOcean, Vultr, Linode
# Recommended: DigitalOcean Droplet ($12/month = PKR 3,360/month)

# 2. Server Specs (Start Small)
# - 2 CPU cores
# - 4GB RAM
# - 80GB SSD
# - Ubuntu 22.04 LTS
# Cost: PKR 5,000-10,000/month

# 3. Initial Setup
ssh root@your-server-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# 4. Deploy
git clone https://github.com/yourrepo/agentic-event-orchestrator.git
cd agentic-event-orchestrator

# Set environment variables
cp .env.example .env
nano .env  # Add your API keys

# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

---

## Updated Budget (Pakistan Context)

### Development Phase (6 Months)

| Category | Monthly (PKR) | Total (PKR) |
|----------|---------------|-------------|
| **Team Salaries** | | |
| - 2 Backend Developers (PKR 80k each) | 160,000 | 960,000 |
| - 1 Frontend Developer (PKR 70k) | 70,000 | 420,000 |
| - 1 DevOps (PKR 60k) | 60,000 | 360,000 |
| - 1 QA Tester (PKR 50k) | 50,000 | 300,000 |
| **Infrastructure** | | |
| - VPS Server (DigitalOcean) | 5,000 | 30,000 |
| - Domain + SSL | 500 | 3,000 |
| - Database Backup Storage | 1,000 | 6,000 |
| **AI APIs** | | |
| - Anthropic Claude API | 15,000 | 90,000 |
| - OpenAI (Fallback) | 10,000 | 60,000 |
| **Other Services** | | |
| - SendGrid (Email) | 2,000 | 12,000 |
| - Stripe/JazzCash (Payment) | 1,500 | 9,000 |
| - SMS Service (Twilio/Local) | 2,000 | 12,000 |
| **Development Tools** | | |
| - GitHub Pro | 1,500 | 9,000 |
| - Design Tools (Figma) | 1,000 | 6,000 |
| **Contingency (10%)** | 36,000 | 216,000 |
| **TOTAL** | **400,000** | **2,493,000** |

**~PKR 2.5 Million for 6 months** (Much more realistic for Pakistan!)

### Monthly Operating Costs (After Launch)

| Service | Monthly Cost (PKR) |
|---------|-------------------|
| VPS Server (Production) | 10,000 |
| Database Backups | 2,000 |
| Claude API (~1000 events/month) | 20,000 |
| SendGrid (10,000 emails) | 3,000 |
| Payment Gateway Fees | 5,000 |
| SMS Notifications | 3,000 |
| Domain + SSL | 500 |
| Monitoring Tools | 2,000 |
| **TOTAL** | **45,500/month** |

**Much cheaper than PKR 72,000/month!**

---

## Vendor Registration System - Complete Flow

### 1. Vendor Registration API

```python
# services/backend/app/api/vendor_registration.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uuid

router = APIRouter(prefix="/api/vendors", tags=["Vendor Management"])

class VendorRegistration(BaseModel):
    email: EmailStr
    password: str
    business_name: str
    owner_name: str
    phone: str
    category: str  # "catering", "venue", "decoration", etc.
    service_areas: List[str]  # ["Lahore", "Islamabad", "Karachi"]
    pricing_min: Optional[float] = None
    pricing_max: Optional[float] = None
    description: str
    cnic: str  # For verification in Pakistan
    business_registration: Optional[str] = None  # NTN or business license

class VendorProfile(BaseModel):
    vendor_id: str
    business_name: str
    category: str
    description: str
    service_areas: List[str]
    pricing_range: str
    rating: float
    total_reviews: int
    verification_status: str  # "pending", "verified", "rejected"
    portfolio_images: List[str]

@router.post("/register")
async def register_vendor(vendor: VendorRegistration):
    """
    Register a new vendor.
    
    Process:
    1. Create user account (role: "vendor")
    2. Create vendor profile (status: "pending")
    3. Send verification email
    4. Notify admin for manual verification
    """
    
    # Check if email already exists
    existing_user = await db.users.find_one({"email": vendor.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user account
    user_id = str(uuid.uuid4())
    password_hash = hash_password(vendor.password)
    
    await db.users.insert_one({
        "user_id": user_id,
        "email": vendor.email,
        "password_hash": password_hash,
        "full_name": vendor.owner_name,
        "phone": vendor.phone,
        "role": "vendor",
        "is_verified": False,
        "created_at": datetime.utcnow()
    })
    
    # Create vendor profile
    vendor_id = str(uuid.uuid4())
    await db.vendors.insert_one({
        "vendor_id": vendor_id,
        "user_id": user_id,
        "business_name": vendor.business_name,
        "category": vendor.category,
        "description": vendor.description,
        "service_areas": vendor.service_areas,
        "pricing_min": vendor.pricing_min,
        "pricing_max": vendor.pricing_max,
        "cnic": encrypt(vendor.cnic),  # Encrypted for security
        "business_registration": vendor.business_registration,
        "verification_status": "pending",  # Requires admin approval
        "rating": 0.0,
        "total_reviews": 0,
        "is_api_integrated": False,
        "created_at": datetime.utcnow()
    })
    
    # Send verification email
    await send_vendor_verification_email(vendor.email, vendor_id)
    
    # Notify admin
    await notify_admin_new_vendor_pending(vendor_id)
    
    return {
        "status": "success",
        "message": "Registration successful! Your profile is pending verification.",
        "vendor_id": vendor_id,
        "next_steps": [
            "Check your email for verification link",
            "Upload portfolio images",
            "Wait for admin approval (usually 24-48 hours)"
        ]
    }

@router.post("/upload-portfolio/{vendor_id}")
async def upload_portfolio_images(
    vendor_id: str,
    images: List[UploadFile] = File(...),
    current_vendor = Depends(verify_vendor_token)
):
    """
    Upload portfolio images for vendor profile.
    Maximum 10 images, each up to 5MB.
    """
    
    if len(images) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")
    
    uploaded_urls = []
    
    for image in images:
        # Validate image
        if image.size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(status_code=400, detail=f"Image {image.filename} exceeds 5MB")
        
        # Upload to storage (local or S3/Cloudinary)
        image_url = await upload_image_to_storage(image, vendor_id)
        uploaded_urls.append(image_url)
    
    # Update vendor profile
    await db.vendors.update_one(
        {"vendor_id": vendor_id},
        {"$push": {"portfolio_images": {"$each": uploaded_urls}}}
    )
    
    return {
        "status": "success",
        "uploaded_images": uploaded_urls
    }

@router.get("/profile/{vendor_id}")
async def get_vendor_profile(vendor_id: str):
    """Get public vendor profile"""
    
    vendor = await db.vendors.find_one({"vendor_id": vendor_id})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Don't return sensitive info (CNIC, etc.)
    return VendorProfile(
        vendor_id=vendor["vendor_id"],
        business_name=vendor["business_name"],
        category=vendor["category"],
        description=vendor["description"],
        service_areas=vendor["service_areas"],
        pricing_range=f"PKR {vendor['pricing_min']:,.0f} - {vendor['pricing_max']:,.0f}",
        rating=vendor["rating"],
        total_reviews=vendor["total_reviews"],
        verification_status=vendor["verification_status"],
        portfolio_images=vendor.get("portfolio_images", [])
    )

@router.put("/update-availability/{vendor_id}")
async def update_availability(
    vendor_id: str,
    availability: dict,
    current_vendor = Depends(verify_vendor_token)
):
    """
    Update vendor availability calendar.
    
    availability = {
        "2026-02-15": {"available": true, "time_slots": ["morning", "evening"]},
        "2026-02-20": {"available": false, "reason": "Booked"}
    }
    """
    
    await db.vendors.update_one(
        {"vendor_id": vendor_id},
        {"$set": {"availability_calendar": availability}}
    )
    
    return {"status": "success", "message": "Availability updated"}
```

### 2. Admin Verification Interface

```python
# services/backend/app/api/admin_verification.py

@router.get("/admin/pending-vendors")
async def get_pending_vendors(current_admin = Depends(verify_admin_token)):
    """Get all vendors pending verification"""
    
    pending = await db.vendors.find({
        "verification_status": "pending"
    }).to_list(100)
    
    return {
        "count": len(pending),
        "vendors": pending
    }

@router.post("/admin/verify-vendor/{vendor_id}")
async def verify_vendor(
    vendor_id: str,
    approved: bool,
    rejection_reason: Optional[str] = None,
    current_admin = Depends(verify_admin_token)
):
    """
    Approve or reject vendor registration.
    
    Admin checks:
    - Business legitimacy
    - Contact information validity
    - Portfolio quality
    - CNIC verification (in Pakistan context)
    """
    
    if approved:
        # Approve vendor
        await db.vendors.update_one(
            {"vendor_id": vendor_id},
            {"$set": {
                "verification_status": "verified",
                "verified_at": datetime.utcnow(),
                "verified_by": current_admin["user_id"]
            }}
        )
        
        # Send approval email
        vendor = await db.vendors.find_one({"vendor_id": vendor_id})
        user = await db.users.find_one({"user_id": vendor["user_id"]})
        
        await send_vendor_approved_email(user["email"], vendor["business_name"])
        
        return {
            "status": "success",
            "message": f"Vendor {vendor['business_name']} approved!"
        }
    else:
        # Reject vendor
        await db.vendors.update_one(
            {"vendor_id": vendor_id},
            {"$set": {
                "verification_status": "rejected",
                "rejection_reason": rejection_reason,
                "rejected_at": datetime.utcnow()
            }}
        )
        
        # Send rejection email
        vendor = await db.vendors.find_one({"vendor_id": vendor_id})
        user = await db.users.find_one({"user_id": vendor["user_id"]})
        
        await send_vendor_rejected_email(
            user["email"], 
            vendor["business_name"],
            rejection_reason
        )
        
        return {
            "status": "success",
            "message": "Vendor registration rejected"
        }
```

### 3. Vendor Portal Frontend

```typescript
// frontend/vendor-portal/app/register/page.tsx

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';

export default function VendorRegistration() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    business_name: '',
    owner_name: '',
    phone: '',
    category: '',
    service_areas: [],
    pricing_min: '',
    pricing_max: '',
    description: '',
    cnic: '',
  });

  const categories = [
    'Catering',
    'Venue',
    'Decoration',
    'Photography',
    'Music/DJ',
    'Transportation',
    'Makeup Artist',
    'Event Planning',
  ];

  const cities = [
    'Lahore',
    'Karachi',
    'Islamabad',
    'Rawalpindi',
    'Faisalabad',
    'Multan',
    'Peshawar',
    'Quetta',
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const response = await fetch('/api/vendors/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData),
    });

    const result = await response.json();

    if (result.status === 'success') {
      // Show success message
      alert('Registration successful! Check your email for verification.');
      // Redirect to portfolio upload
      window.location.href = `/vendor/upload-portfolio/${result.vendor_id}`;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-3xl font-bold mb-8">Register as a Vendor</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Account Information */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Account Information</h2>
          
          <Input
            label="Email"
            type="email"
            required
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
          />
          
          <Input
            label="Password"
            type="password"
            required
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
          />
        </div>

        {/* Business Information */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Business Information</h2>
          
          <Input
            label="Business Name"
            required
            value={formData.business_name}
            onChange={(e) => setFormData({...formData, business_name: e.target.value})}
          />
          
          <Input
            label="Owner Name"
            required
            value={formData.owner_name}
            onChange={(e) => setFormData({...formData, owner_name: e.target.value})}
          />
          
          <Input
            label="Phone (WhatsApp)"
            placeholder="+92 300 1234567"
            required
            value={formData.phone}
            onChange={(e) => setFormData({...formData, phone: e.target.value})}
          />
          
          <Input
            label="CNIC Number"
            placeholder="12345-1234567-1"
            required
            value={formData.cnic}
            onChange={(e) => setFormData({...formData, cnic: e.target.value})}
          />
        </div>

        {/* Service Details */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Service Details</h2>
          
          <Select
            label="Category"
            required
            value={formData.category}
            onChange={(value) => setFormData({...formData, category: value})}
            options={categories}
          />
          
          <MultiSelect
            label="Service Areas (Cities)"
            required
            value={formData.service_areas}
            onChange={(areas) => setFormData({...formData, service_areas: areas})}
            options={cities}
          />
          
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Minimum Price (PKR)"
              type="number"
              placeholder="50,000"
              value={formData.pricing_min}
              onChange={(e) => setFormData({...formData, pricing_min: e.target.value})}
            />
            
            <Input
              label="Maximum Price (PKR)"
              type="number"
              placeholder="200,000"
              value={formData.pricing_max}
              onChange={(e) => setFormData({...formData, pricing_max: e.target.value})}
            />
          </div>
          
          <Textarea
            label="Business Description"
            required
            rows={4}
            placeholder="Describe your services, experience, and what makes you unique..."
            value={formData.description}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
          />
        </div>

        <Button type="submit" className="w-full">
          Register as Vendor
        </Button>
      </form>

      <div className="mt-8 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-semibold mb-2">What happens next?</h3>
        <ol className="list-decimal list-inside space-y-1 text-sm">
          <li>We'll send you a verification email</li>
          <li>Upload your portfolio images</li>
          <li>Our team will verify your profile (24-48 hours)</li>
          <li>Once approved, you'll start receiving booking requests!</li>
        </ol>
      </div>
    </div>
  );
}
```

---

## Scalability Strategy - Practical Steps

### Stage 1: MVP (0-500 events/month)

**Infrastructure**:
- 1 VPS (4GB RAM, 2 CPU)
- Docker Compose
- PostgreSQL + Redis on same server
- Cost: PKR 10,000/month

**Can Handle**:
- 100 concurrent users
- 500 events/month
- 50 vendors
- 10,000 page views/day

**When to Upgrade**: When you hit 300+ events/month consistently

### Stage 2: Growth (500-5,000 events/month)

**Infrastructure Changes**:
```
┌─────────────────┐      ┌─────────────────┐
│  VPS 1          │      │  VPS 2          │
│  Frontend       │      │  Backend API    │
│  (Next.js)      │◄────►│  (FastAPI)      │
└─────────────────┘      └─────────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │  Managed PostgreSQL  │
                    │  (DigitalOcean DBaaS)│
                    └──────────────────────┘
```

**Upgrade Path**:
1. Move database to managed service (DigitalOcean DBaaS)
2. Separate frontend and backend servers
3. Add Redis cluster
4. Add load balancer (NGINX)

**Cost**: PKR 40,000-50,000/month

**Can Handle**:
- 500 concurrent users
- 5,000 events/month
- 500 vendors
- 100,000 page views/day

### Stage 3: Scale (5,000+ events/month)

**Now consider Kubernetes** (or stick with multiple VPS + load balancer)

**Upgrade Indicators**:
- Consistent 5,000+ events/month
- 1,000+ concurrent users
- Multiple countries/regions
- Need for auto-scaling

---

## Simplified Technology Stack (No Kubernetes)

### Backend
- **Python 3.11** + **FastAPI**
- **PostgreSQL** (managed or self-hosted)
- **Redis** (caching)
- **LangChain** (AI orchestration)
- **Claude Sonnet 4** (primary LLM)

### Frontend
- **Next.js 14** + **React**
- **Tailwind CSS**
- **shadcn/ui**

### Deployment
- **Docker Compose** (Stage 1-2)
- **PM2** or **Systemd** (if not using Docker)
- **NGINX** (reverse proxy)

### Hosting (Pakistan-friendly)
- **DigitalOcean** (recommended, PKR payment via cards)
- **Vultr** (good Pakistan routing)
- **Local**: Hostinger Pakistan, Truehost

---

## Payment Integration (Pakistan Context)

### Local Payment Gateways

```python
# Support both international and local payments

PAYMENT_GATEWAYS = {
    "stripe": {  # For international cards
        "enabled": True,
        "currencies": ["USD", "PKR"]
    },
    "jazzcash": {  # Local Pakistan
        "enabled": True,
        "currencies": ["PKR"]
    },
    "easypaisa": {  # Local Pakistan
        "enabled": True,
        "currencies": ["PKR"]
    },
    "cash": {  # Cash on delivery/event
        "enabled": True,
        "currencies": ["PKR"]
    }
}
```

### Pricing in PKR

```python
# All internal pricing in PKR

class Event(BaseModel):
    budget_min: float  # PKR
    budget_max: float  # PKR

class Vendor(BaseModel):
    pricing_min: float  # PKR
    pricing_max: float  # PKR
    
# Example
event = Event(
    budget_min=50000,   # PKR 50,000
    budget_max=200000   # PKR 2,00,000
)
```

---

## Quick Start Guide (No Kubernetes!)

### Option 1: Local Development

```bash
# 1. Clone repository
git clone https://github.com/yourrepo/agentic-event-orchestrator.git
cd agentic-event-orchestrator

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start with Docker Compose
docker compose up -d

# 4. Access
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Deploy to VPS

```bash
# 1. Get a VPS (DigitalOcean recommended)
# Specs: 4GB RAM, 2 CPU, 80GB SSD
# Cost: ~PKR 10,000/month

# 2. SSH into server
ssh root@your-server-ip

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 4. Clone and deploy
git clone https://github.com/yourrepo/agentic-event-orchestrator.git
cd agentic-event-orchestrator

# Set environment
nano .env  # Add your keys

# Deploy
docker compose -f docker-compose.prod.yml up -d

# 5. Set up domain (optional)
# Point your domain to server IP
# Configure SSL with Let's Encrypt (free)
```

---

## Summary of Changes

✅ **Kubernetes**: NOT necessary! Use Docker Compose  
✅ **Currency**: All prices in PKR (Pakistani Rupees)  
✅ **Vendor Registration**: Complete flow with verification  
✅ **Scalability**: Yes! Grows in stages as you need  
✅ **Simplified**: Focus on getting MVP live quickly  
✅ **Cost**: PKR 2.5M for 6 months (vs PKR 40M+ before)  
✅ **Local**: Pakistan-specific hosting and payment options  

---

## Recommended Timeline

**Month 1-2**: Build core features (no Kubernetes)  
**Month 3**: Deploy to single VPS, beta testing  
**Month 4**: Launch in one city (Lahore/Islamabad)  
**Month 5-6**: Grow to 500 events/month  
**Month 7+**: Scale infrastructure as needed  

**Start simple, scale smart! 🚀**
