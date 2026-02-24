import { Link } from "react-router-dom";

const PRODUCTS = [
  {
    name: "Parity Health",
    description: "Medical bill benchmark analysis against CMS Medicare rates",
    path: "/parity-health/",
    active: true,
  },
  {
    name: "Parity Insurance",
    description: "Insurance claims benchmark intelligence",
    path: null,
    active: false,
  },
  {
    name: "Parity Property",
    description: "Property assessment benchmark analysis",
    path: null,
    active: false,
  },
];

export default function CivicScaleHomepage() {
  return (
    <div className="min-h-screen bg-[#0E1B2A] flex flex-col font-[Arial,sans-serif]">
      {/* Header */}
      <header className="pt-12 pb-4 px-6 text-center">
        <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
          CivicScale
        </h1>
        <p className="mt-3 text-lg text-gray-400">
          Institutional Benchmark Infrastructure
        </p>
      </header>

      {/* Product Cards */}
      <main className="flex-1 flex items-start justify-center px-6 pt-12 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full">
          {PRODUCTS.map((product) => (
            <ProductCard key={product.name} product={product} />
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 px-6 text-center border-t border-white/10">
        <p className="text-xs text-gray-500">
          CivicScale benchmark infrastructure. Benchmark comparisons use
          publicly available government data. Not legal advice.
        </p>
        <p className="text-xs text-gray-600 mt-1">&copy; CivicScale 2026</p>
      </footer>
    </div>
  );
}

function ProductCard({ product }) {
  const baseClasses =
    "rounded-xl p-6 border transition-all duration-200 text-left";

  if (product.active) {
    return (
      <Link
        to={product.path}
        className={`${baseClasses} bg-white/5 border-[#0D7377]/40 hover:border-[#0D7377] hover:bg-white/10 cursor-pointer block`}
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-white">{product.name}</h2>
          <span className="text-xs font-medium text-[#0D7377] bg-[#0D7377]/15 px-2 py-0.5 rounded-full">
            Live
          </span>
        </div>
        <p className="text-sm text-gray-400 leading-relaxed">
          {product.description}
        </p>
        <div className="mt-4 text-sm font-medium text-[#0D7377]">
          Open &rarr;
        </div>
      </Link>
    );
  }

  return (
    <div
      className={`${baseClasses} bg-white/[0.02] border-white/10 opacity-50`}
    >
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-gray-400">{product.name}</h2>
        <span className="text-xs font-medium text-gray-500 bg-white/5 px-2 py-0.5 rounded-full">
          Coming Soon
        </span>
      </div>
      <p className="text-sm text-gray-500 leading-relaxed">
        {product.description}
      </p>
    </div>
  );
}
