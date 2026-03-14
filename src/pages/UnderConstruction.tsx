import { useEffect, useState } from "react";
import { Hammer, Wrench } from "lucide-react";

export default function UnderConstruction({ title }: { title: string }) {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((d) => (d.length >= 3 ? "" : d + "."));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] p-8 overflow-hidden">
      <style>{`
        @keyframes bounce-slow {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }
      `}</style>

      {/* Icons */}
      <div className="flex items-center gap-4 animate-[bounce-slow_2s_ease-in-out_infinite] mb-6">
        <Hammer className="h-14 w-14 text-primary" />
        <Wrench className="h-14 w-14 text-primary" />
      </div>

      {/* Title */}
      <h1 className="text-3xl font-bold text-foreground mb-2">{title}</h1>
      <p className="text-lg text-muted-foreground mb-8">
        Em construção{dots}
      </p>
      <p className="text-sm text-muted-foreground mb-12 max-w-md text-center">
        Estamos trabalhando duro para preparar esta página para você! 🚧🔨
      </p>
    </div>
  );
}