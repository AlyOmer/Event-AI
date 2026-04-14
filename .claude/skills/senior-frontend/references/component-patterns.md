# Component Patterns Reference

## Auth Forms

### Login Page (full template)
```tsx
"use client";
import { useState, Suspense } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Calendar, Eye, EyeOff, Loader2 } from "lucide-react";
import { cn } from "@event-ai/ui";
import toast from "react-hot-toast";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    try {
      // call API
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.message || "Login failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-purple-50 px-4">
      <div className="w-full max-w-md">
        {/* Card */}
        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg mb-4">
              <Calendar className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Welcome back</h1>
            <p className="mt-1 text-sm text-gray-500">Sign in to your Event-AI account</p>
          </div>

          {/* Google OAuth */}
          <button className="w-full flex items-center justify-center gap-3 rounded-xl border border-gray-200
                             bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-sm
                             hover:bg-gray-50 hover:border-gray-300 active:scale-[0.98]
                             transition-all duration-150 mb-6">
            {/* Google SVG icon */}
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-3 text-gray-400 font-medium tracking-wider">or</span>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-gray-700">Email address</label>
              <input
                {...register("email")}
                type="email"
                placeholder="you@example.com"
                className={cn(
                  "w-full rounded-xl border px-4 py-3 text-sm shadow-sm transition-all duration-150",
                  "placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
                  errors.email ? "border-red-300 bg-red-50/50" : "border-gray-200 bg-white hover:border-gray-300"
                )}
              />
              {errors.email && <p className="text-xs text-red-600 flex items-center gap-1">{errors.email.message}</p>}
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700">Password</label>
                <Link href="/forgot-password" className="text-xs text-indigo-600 hover:text-indigo-700 font-medium">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  {...register("password")}
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  className={cn(
                    "w-full rounded-xl border px-4 py-3 pr-11 text-sm shadow-sm transition-all duration-150",
                    "placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
                    errors.password ? "border-red-300 bg-red-50/50" : "border-gray-200 bg-white hover:border-gray-300"
                  )}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && <p className="text-xs text-red-600">{errors.password.message}</p>}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700
                         px-4 py-3 text-sm font-semibold text-white shadow-sm
                         hover:from-indigo-700 hover:to-indigo-800 active:scale-[0.98]
                         disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-150"
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {isSubmitting ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500">
            Don't have an account?{" "}
            <Link href="/signup" className="font-semibold text-indigo-600 hover:text-indigo-700">
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
```

---

## Vendor / Product Cards

```tsx
interface VendorCardProps {
  name: string;
  category: string;
  rating: number;
  reviewCount: number;
  location: string;
  priceRange: string;
  imageUrl?: string;
  verified?: boolean;
}

function VendorCard({ name, category, rating, reviewCount, location, priceRange, verified }: VendorCardProps) {
  return (
    <div className="group rounded-2xl bg-white border border-gray-100 shadow-sm
                    hover:shadow-lg hover:-translate-y-1 transition-all duration-300 overflow-hidden cursor-pointer">
      {/* Image */}
      <div className="aspect-[4/3] bg-gradient-to-br from-indigo-50 to-purple-50 relative overflow-hidden">
        <div className="absolute inset-0 flex items-center justify-center">
          <Store className="h-12 w-12 text-indigo-200" />
        </div>
        {verified && (
          <div className="absolute top-3 left-3">
            <span className="inline-flex items-center gap-1 rounded-full bg-green-500 px-2.5 py-1 text-xs font-semibold text-white shadow-sm">
              <CheckCircle className="h-3 w-3" /> Verified
            </span>
          </div>
        )}
        <div className="absolute top-3 right-3">
          <span className="rounded-full bg-white/90 backdrop-blur-sm px-2.5 py-1 text-xs font-semibold text-gray-700 shadow-sm">
            {priceRange}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 truncate group-hover:text-indigo-600 transition-colors">
              {name}
            </h3>
            <p className="text-sm text-gray-500 mt-0.5">{category}</p>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <Star className="h-4 w-4 fill-amber-400 text-amber-400" />
            <span className="text-sm font-semibold text-gray-900">{rating.toFixed(1)}</span>
            <span className="text-xs text-gray-400">({reviewCount})</span>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-1.5 text-xs text-gray-500">
          <MapPin className="h-3.5 w-3.5 shrink-0" />
          {location}
        </div>
      </div>
    </div>
  );
}
```

---

## Dashboard Stats Row

```tsx
const stats = [
  { label: "Total Events", value: "12", change: "+2 this month", icon: Calendar, color: "indigo" },
  { label: "Active Bookings", value: "4", change: "3 pending", icon: Package, color: "blue" },
  { label: "Vendors Contacted", value: "28", change: "+5 this week", icon: Store, color: "purple" },
  { label: "Messages", value: "47", change: "3 unread", icon: MessageSquare, color: "green" },
];

const colorMap = {
  indigo: "bg-indigo-50 text-indigo-600",
  blue: "bg-blue-50 text-blue-600",
  purple: "bg-purple-50 text-purple-600",
  green: "bg-green-50 text-green-600",
};

function StatsRow() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, i) => (
        <div
          key={stat.label}
          className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5
                     hover:shadow-md transition-shadow duration-200"
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500">{stat.label}</span>
            <div className={cn("rounded-xl p-2", colorMap[stat.color as keyof typeof colorMap])}>
              <stat.icon className="h-4 w-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
          <p className="mt-1 text-xs text-gray-400">{stat.change}</p>
        </div>
      ))}
    </div>
  );
}
```

---

## Modal / Dialog

```tsx
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";

function Modal({ open, onClose, title, children }: {
  open: boolean; onClose: () => void; title: string; children: React.ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 animate-fadeIn" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50
                                   w-full max-w-lg bg-white rounded-2xl shadow-2xl p-6
                                   focus:outline-none animate-slideIn">
          <div className="flex items-center justify-between mb-5">
            <Dialog.Title className="text-lg font-semibold text-gray-900">{title}</Dialog.Title>
            <Dialog.Close className="rounded-lg p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

---

## Search Bar with Filters

```tsx
function SearchBar({ onSearch }: { onSearch: (q: string) => void }) {
  return (
    <div className="flex gap-3">
      <div className="relative flex-1">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="search"
          placeholder="Search vendors, services..."
          onChange={(e) => onSearch(e.target.value)}
          className="w-full rounded-xl border border-gray-200 bg-white pl-10 pr-4 py-3 text-sm
                     shadow-sm placeholder:text-gray-400 focus:outline-none focus:ring-2
                     focus:ring-indigo-500 focus:border-transparent hover:border-gray-300
                     transition-all duration-150"
        />
      </div>
      <button className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white
                         px-4 py-3 text-sm font-medium text-gray-700 shadow-sm
                         hover:bg-gray-50 transition-colors">
        <SlidersHorizontal className="h-4 w-4" />
        Filters
      </button>
    </div>
  );
}
```

---

## Notification Toast Patterns

```tsx
// Success
toast.success("Booking confirmed!", { icon: "🎉" });

// Error
toast.error("Something went wrong. Please try again.");

// Loading → Success
const toastId = toast.loading("Saving changes...");
// after async
toast.success("Saved!", { id: toastId });
```

---

## Skeleton Loaders

```tsx
function VendorCardSkeleton() {
  return (
    <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden animate-pulse">
      <div className="aspect-[4/3] bg-gray-100" />
      <div className="p-5 space-y-3">
        <div className="h-4 bg-gray-100 rounded-full w-3/4" />
        <div className="h-3 bg-gray-100 rounded-full w-1/2" />
        <div className="h-3 bg-gray-100 rounded-full w-2/3" />
      </div>
    </div>
  );
}
```
