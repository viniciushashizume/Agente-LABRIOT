import { useEffect, useState } from "react";
import { Construction } from "lucide-react";

interface Bunny {
  id: number;
  x: number;
  y: number;
  speed: number;
  direction: number;
  action: "walking" | "hammering" | "carrying";
  flip: boolean;
}

const BunnySVG = ({ action, flip }: { action: string; flip: boolean }) => {
  const transform = flip ? "scaleX(-1)" : "";
  
  return (
    <div className="relative" style={{ transform, width: 48, height: 48 }}>
      {/* Bunny body */}
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2">
        {/* Ears */}
        <div className="flex gap-1 justify-center -mb-1">
          <div className="w-2 h-5 bg-pink-200 rounded-full rotate-[-10deg]" />
          <div className="w-2 h-5 bg-pink-200 rounded-full rotate-[10deg]" />
        </div>
        {/* Head */}
        <div className="w-6 h-6 bg-pink-100 rounded-full mx-auto relative">
          <div className="absolute top-2 left-1.5 w-1 h-1 bg-foreground rounded-full" />
          <div className="absolute top-2 right-1.5 w-1 h-1 bg-foreground rounded-full" />
          <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2 w-1.5 h-1 bg-pink-300 rounded-full" />
        </div>
        {/* Body */}
        <div className="w-7 h-5 bg-pink-100 rounded-lg mx-auto -mt-1" />
        {/* Tool */}
        {action === "hammering" && (
          <div className="absolute -right-3 top-4 animate-[hammer_0.5s_ease-in-out_infinite]">
            <div className="w-1 h-5 bg-yellow-700 rounded-sm origin-bottom" />
            <div className="w-3 h-2 bg-muted-foreground rounded-sm -mt-0.5 -ml-1" />
          </div>
        )}
        {action === "carrying" && (
          <div className="absolute -top-2 left-1/2 -translate-x-1/2">
            <div className="w-5 h-3 bg-yellow-600 rounded-sm border border-yellow-700" />
          </div>
        )}
      </div>
    </div>
  );
};

const FloatingBrick = ({ delay, x }: { delay: number; x: number }) => (
  <div
    className="absolute bottom-0"
    style={{
      left: `${x}%`,
      animation: `brickStack 3s ease-in-out ${delay}s infinite`,
    }}
  >
    <div className="w-8 h-4 bg-orange-400 rounded-sm border border-orange-500 opacity-70" />
  </div>
);

export default function UnderConstruction({ title }: { title: string }) {
  const [bunnies, setBunnies] = useState<Bunny[]>([]);
  const [dots, setDots] = useState("");

  useEffect(() => {
    const initial: Bunny[] = Array.from({ length: 4 }, (_, i) => ({
      id: i,
      x: 15 + i * 20,
      y: 0,
      speed: 0.3 + Math.random() * 0.4,
      direction: Math.random() > 0.5 ? 1 : -1,
      action: (["walking", "hammering", "carrying"] as const)[i % 3],
      flip: Math.random() > 0.5,
    }));
    setBunnies(initial);

    const interval = setInterval(() => {
      setBunnies((prev) =>
        prev.map((b) => {
          let newX = b.x + b.speed * b.direction;
          let newDir = b.direction;
          let newFlip = b.flip;
          if (newX > 85) { newDir = -1; newFlip = true; }
          if (newX < 5) { newDir = 1; newFlip = false; }
          return { ...b, x: newX, direction: newDir, flip: newFlip };
        })
      );
    }, 50);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((d) => (d.length >= 3 ? "" : d + "."));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] p-8 overflow-hidden">
      <style>{`
        @keyframes hammer {
          0%, 100% { transform: rotate(0deg); }
          50% { transform: rotate(-30deg); }
        }
        @keyframes brickStack {
          0% { transform: translateY(0); opacity: 0; }
          20% { opacity: 1; }
          80% { transform: translateY(-60px); opacity: 1; }
          100% { transform: translateY(-60px); opacity: 0; }
        }
        @keyframes bounce-slow {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }
      `}</style>

      {/* Icon */}
      <div className="animate-[bounce-slow_2s_ease-in-out_infinite] mb-6">
        <Construction className="h-16 w-16 text-primary" />
      </div>

      {/* Title */}
      <h1 className="text-3xl font-bold text-foreground mb-2">{title}</h1>
      <p className="text-lg text-muted-foreground mb-8">
        Em construção{dots}
      </p>
      <p className="text-sm text-muted-foreground mb-12 max-w-md text-center">
        Nossos coelhos construtores estão trabalhando duro para preparar esta página! 🐰🔨
      </p>

      {/* Construction scene */}
      <div className="relative w-full max-w-2xl h-40 bg-muted/30 rounded-xl border border-border overflow-hidden">
        {/* Ground */}
        <div className="absolute bottom-0 left-0 right-0 h-8 bg-muted/50 rounded-b-xl" />

        {/* Bricks */}
        {[10, 30, 50, 70, 85].map((x, i) => (
          <FloatingBrick key={i} delay={i * 0.6} x={x} />
        ))}

        {/* Bunnies */}
        {bunnies.map((bunny) => (
          <div
            key={bunny.id}
            className="absolute bottom-6 transition-none"
            style={{
              left: `${bunny.x}%`,
              animation: "bounce-slow 1s ease-in-out infinite",
              animationDelay: `${bunny.id * 0.2}s`,
            }}
          >
            <BunnySVG action={bunny.action} flip={bunny.flip} />
          </div>
        ))}

        {/* Scaffolding */}
        <div className="absolute right-8 bottom-8 w-1 h-24 bg-yellow-700/60 rounded" />
        <div className="absolute right-16 bottom-8 w-1 h-24 bg-yellow-700/60 rounded" />
        <div className="absolute right-8 bottom-20 w-9 h-1 bg-yellow-700/60 rounded" />
        <div className="absolute right-8 bottom-28 w-9 h-1 bg-yellow-700/60 rounded" />
      </div>
    </div>
  );
}
