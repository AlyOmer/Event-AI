# Page Templates Reference

## Hero Section (Landing Page)

```tsx
<section className="relative overflow-hidden bg-gradient-to-br from-indigo-50 via-white to-purple-50 px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
  {/* Background decoration */}
  <div className="absolute inset-0 -z-10 overflow-hidden">
    <div className="absolute -top-40 -right-32 h-96 w-96 rounded-full bg-indigo-100/60 blur-3xl" />
    <div className="absolute -bottom-40 -left-32 h-96 w-96 rounded-full bg-purple-100/60 blur-3xl" />
  </div>

  <div className="mx-auto max-w-4xl text-center">
    {/* Badge */}
    <div className="inline-flex items-center gap-2 rounded-full bg-indigo-50 border border-indigo-100
                    px-4 py-1.5 text-sm font-semibold text-indigo-700 mb-6 animate-fadeInDown">
      <Sparkles className="h-4 w-4" />
      AI-Powered Event Planning
    </div>

    {/* Headline */}
    <h1 className="text-5xl sm:text-6xl font-bold tracking-tight text-gray-900 leading-tight animate-fadeInUp">
      Plan Your Perfect Event
      <br />
      <span className="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
        in Pakistan
      </span>
    </h1>

    {/* Subheadline */}
    <p className="mt-6 text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed animate-fadeInUp"
       style={{ animationDelay: "100ms" }}>
      Discover top vendors, get AI recommendations, and plan weddings,
      birthdays, corporate events, and more with ease.
    </p>

    {/* CTAs */}
    <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 animate-fadeInUp"
         style={{ animationDelay: "200ms" }}>
      <Link href="/create-event"
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700
                       px-8 py-4 text-base font-semibold text-white shadow-lg shadow-indigo-200
                       hover:from-indigo-700 hover:to-indigo-800 hover:shadow-xl hover:shadow-indigo-200
                       active:scale-[0.98] transition-all duration-200">
        Start Planning <ArrowRight className="h-5 w-5" />
      </Link>
      <Link href="/marketplace"
            className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white
                       px-8 py-4 text-base font-semibold text-gray-700 shadow-sm
                       hover:bg-gray-50 hover:border-gray-300 hover:shadow
                       active:scale-[0.98] transition-all duration-200">
        Browse Vendors
      </Link>
    </div>

    {/* Social proof */}
    <div className="mt-12 flex items-center justify-center gap-8 text-sm text-gray-500 animate-fadeInUp"
         style={{ animationDelay: "300ms" }}>
      <div className="flex items-center gap-2">
        <div className="flex -space-x-2">
          {[1,2,3,4].map(i => (
            <div key={i} className="h-8 w-8 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500
                                    border-2 border-white" />
          ))}
        </div>
        <span>10,000+ events planned</span>
      </div>
      <div className="flex items-center gap-1.5">
        {[1,2,3,4,5].map(i => <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />)}
        <span>4.9/5 rating</span>
      </div>
    </div>
  </div>
</section>
```

## Feature Grid (3-column)

```tsx
const features = [
  { icon: Search, title: "Smart Discovery", description: "AI-powered vendor matching based on your event type, budget, and location.", color: "indigo" },
  { icon: Calendar, title: "Event Planning", description: "Create detailed event plans with timelines, checklists, and vendor coordination.", color: "blue" },
  { icon: MessageSquare, title: "Direct Messaging", description: "Chat with vendors, negotiate prices, and confirm bookings in one place.", color: "purple" },
  { icon: Shield, title: "Verified Vendors", description: "Every vendor is verified, reviewed, and rated by real customers.", color: "green" },
  { icon: Sparkles, title: "AI Assistant", description: "Get personalized recommendations and answers to all your event questions.", color: "amber" },
  { icon: CreditCard, title: "Secure Payments", description: "Pay safely with escrow protection and full refund guarantee.", color: "rose" },
];

const iconColors = {
  indigo: "bg-indigo-50 text-indigo-600",
  blue: "bg-blue-50 text-blue-600",
  purple: "bg-purple-50 text-purple-600",
  green: "bg-green-50 text-green-600",
  amber: "bg-amber-50 text-amber-600",
  rose: "bg-rose-50 text-rose-600",
};

<section className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
  <div className="mx-auto max-w-7xl">
    <div className="text-center mb-16">
      <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">Everything You Need</h2>
      <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
        From vendor discovery to booking management, we have you covered.
      </p>
    </div>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {features.map((feature, i) => (
        <div
          key={feature.title}
          className="group rounded-2xl border border-gray-100 bg-white p-6 shadow-sm
                     hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 animate-fadeInUp"
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <div className={cn("inline-flex rounded-xl p-3 mb-4", iconColors[feature.color as keyof typeof iconColors])}>
            <feature.icon className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
          <p className="text-sm text-gray-600 leading-relaxed">{feature.description}</p>
        </div>
      ))}
    </div>
  </div>
</section>
```

## Marketplace / Vendor Grid Page

```tsx
export default function MarketplacePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Page Header */}
      <div className="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900">Find Vendors</h1>
          <p className="mt-1 text-sm text-gray-500">Discover top-rated vendors for your event</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search + Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-8">
          <SearchBar onSearch={() => {}} />
          {/* Category pills */}
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
            {["All", "Wedding", "Corporate", "Birthday", "Mehndi"].map(cat => (
              <button key={cat}
                      className="shrink-0 rounded-full border border-gray-200 bg-white px-4 py-2
                                 text-sm font-medium text-gray-600 hover:border-indigo-300
                                 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {vendors.map((vendor, i) => (
            <div key={vendor.id} className="animate-fadeInUp" style={{ animationDelay: `${i * 40}ms` }}>
              <VendorCard {...vendor} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

## Dashboard Layout

```tsx
export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Welcome Header */}
      <div className="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Good morning, Ahmed 👋</h1>
            <p className="mt-1 text-sm text-gray-500">Here's what's happening with your events</p>
          </div>
          <Link href="/create-event"
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5
                           text-sm font-semibold text-white hover:bg-indigo-700 transition-colors">
            <Plus className="h-4 w-4" /> New Event
          </Link>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Stats */}
        <StatsRow />

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main: Recent Events */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Recent Events</h2>
              <Link href="/events" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
                View all →
              </Link>
            </div>
            {/* event list */}
          </div>

          {/* Sidebar: Quick Actions */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">Quick Actions</h2>
            {/* action cards */}
          </div>
        </div>
      </div>
    </div>
  );
}
```

## CTA Section

```tsx
<section className="px-4 sm:px-6 lg:px-8 py-20">
  <div className="mx-auto max-w-4xl">
    <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-600 to-purple-700 px-8 py-16 text-center shadow-2xl">
      {/* Decorative blobs */}
      <div className="absolute -top-16 -right-16 h-64 w-64 rounded-full bg-white/10" />
      <div className="absolute -bottom-16 -left-16 h-64 w-64 rounded-full bg-white/10" />

      <div className="relative">
        <h2 className="text-3xl sm:text-4xl font-bold text-white">Ready to Plan Your Event?</h2>
        <p className="mt-4 text-lg text-indigo-100 max-w-xl mx-auto">
          Join thousands of event planners using Event-AI to create memorable experiences.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/register"
                className="rounded-xl bg-white px-8 py-3.5 text-base font-semibold text-indigo-600
                           hover:bg-gray-50 active:scale-[0.98] transition-all duration-150 shadow-lg">
            Create Free Account
          </Link>
          <Link href="/marketplace"
                className="rounded-xl border-2 border-white/40 px-8 py-3.5 text-base font-semibold text-white
                           hover:bg-white/10 active:scale-[0.98] transition-all duration-150">
            Explore Vendors
          </Link>
        </div>
      </div>
    </div>
  </div>
</section>
```
