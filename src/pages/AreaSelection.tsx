import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Code2, Cpu, ArrowRight } from "lucide-react";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";

type AreaCategory = "programming" | "projects" | null;
type ProgrammingLanguage = "python" | "javascript" | "cpp";
type ProjectType = "syna" | "dog-feeder" | "nexa" | "aps";

export default function AreaSelection() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const mode = searchParams.get("mode") || "challenges";
  const [category, setCategory] = useState<AreaCategory>(null);
  const [selectedArea, setSelectedArea] = useState<string>("");

  const handleContinue = () => {
    if (selectedArea) {
      const targetPath = mode === "exam" ? "/exam" : "/challenges";
      navigate(`${targetPath}?area=${encodeURIComponent(selectedArea)}`);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-background to-muted/20">
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10">
        <div className="container px-4 py-4">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            {mode === "exam" ? "Escolha a Área da Prova" : "Escolha sua Área de Aprendizado"}
          </h1>
          <p className="text-sm text-muted-foreground">
            {mode === "exam" 
              ? "Selecione a área que deseja ser avaliado"
              : "Selecione a área que deseja desenvolver"
            }
          </p>
        </div>
      </header>

      <main className="flex-1 overflow-auto">
        <div className="container py-8 px-4 max-w-4xl mx-auto">
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <Card 
              className={`cursor-pointer transition-all hover:shadow-lg ${category === "programming" ? "ring-2 ring-primary" : ""}`}
              onClick={() => {
                setCategory("programming");
                setSelectedArea("");
              }}
            >
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Code2 className="h-6 w-6 text-primary" />
                  <CardTitle>Linguagem de Programação Aplicada</CardTitle>
                </div>
                <CardDescription>
                  Aprenda conceitos de programação com desafios práticos
                </CardDescription>
              </CardHeader>
            </Card>

            <Card 
              className={`cursor-pointer transition-all hover:shadow-lg ${category === "projects" ? "ring-2 ring-primary" : ""}`}
              onClick={() => {
                setCategory("projects");
                setSelectedArea("");
              }}
            >
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Cpu className="h-6 w-6 text-primary" />
                  <CardTitle>Projetos do LabRiot</CardTitle>
                </div>
                <CardDescription>
                  Explore projetos de robótica e IoT desenvolvidos no laboratório
                </CardDescription>
              </CardHeader>
            </Card>
          </div>

          {category === "programming" && (
            <Card>
              <CardHeader>
                <CardTitle>Selecione a Linguagem</CardTitle>
              </CardHeader>
              <CardContent>
                <RadioGroup value={selectedArea} onValueChange={setSelectedArea}>
                  <div className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50">
                    <RadioGroupItem value="python" id="python" />
                    <Label htmlFor="python" className="flex-1 cursor-pointer">
                      Python
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50">
                    <RadioGroupItem value="javascript" id="javascript" />
                    <Label htmlFor="javascript" className="flex-1 cursor-pointer">
                      JavaScript
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50">
                    <RadioGroupItem value="cpp" id="cpp" />
                    <Label htmlFor="cpp" className="flex-1 cursor-pointer">
                      C++
                    </Label>
                  </div>
                </RadioGroup>
              </CardContent>
            </Card>
          )}

          {category === "projects" && (
            <Card>
              <CardHeader>
                <CardTitle>Selecione o Projeto</CardTitle>
              </CardHeader>
              <CardContent>
                <RadioGroup value={selectedArea} onValueChange={setSelectedArea}>
                  <div className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50">
                    <RadioGroupItem value="syna" id="syna" />
                    <Label htmlFor="syna" className="flex-1 cursor-pointer">
                      Syna - Sistema inteligente de automação
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50">
                    <RadioGroupItem value="dog-feeder" id="dog-feeder" />
                    <Label htmlFor="dog-feeder" className="flex-1 cursor-pointer">
                      Alimentador de Cachorros - IoT para pets
                    </Label>
                                  </div>
                <div className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50">
                  <RadioGroupItem value="nexa" id="nexa" />
                  {/* Remove the "/" from the end of the opening Label tag */}
                  <Label htmlFor="nexa" className="flex-1 cursor-pointer">
                    Nexa
                  </Label>
                </div>

                <div className="flex items-center space-x-2 p-3 rounded-lg hover:bg-muted/50">
                  {/* Note: Ensure 'id' matches the 'htmlFor' below (you had "nexa" and "aps" mixed) */}
                  <RadioGroupItem value="aps" id="aps" />
                  <Label htmlFor="aps" className="flex-1 cursor-pointer">
                    APS
                  </Label>
                </div>
                </RadioGroup>
              </CardContent>
            </Card>
          )}

          {selectedArea && (
            <div className="flex justify-end mt-6">
              <Button onClick={handleContinue} size="lg">
                {mode === "exam" ? "Continuar para a Prova" : "Continuar para os Desafios"}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
