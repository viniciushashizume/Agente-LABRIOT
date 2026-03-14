// src/pages/Challenges.tsx
import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Challenge } from "@/types/challenge";
import { ChallengeCard } from "@/components/challenges/ChallengeCard";
import { Button } from "@/components/ui/button";
import { RefreshCw, ArrowLeft, ArrowRight, CheckCircle2, Settings } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
// 1. IMPORTAR A FUNÇÃO DE VALIDAÇÃO
import { generateChallenges, validateChallengeAnswer } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

export default function Challenges() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentChallengeIndex, setCurrentChallengeIndex] = useState(0);
  
  // 2. ADICIONAR ESTADO DE "SUBMETENDO" PARA O CARD
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { toast } = useToast();
  
  const selectedArea = searchParams.get("area") || "";

  useEffect(() => {
    if (!selectedArea) {
      navigate("/area-selection");
    }
  }, [selectedArea, navigate]);

  const generateNewChallenges = async () => {
    setIsLoading(true);
    setChallenges([]);
    setCurrentChallengeIndex(0);

    try {
      // <<< MODIFICADO: Passando 3 como segundo argumento >>>
      const response = await generateChallenges(selectedArea, 3);
      const challengeList = response.challenges;

      if (challengeList && Array.isArray(challengeList) && challengeList.length > 0) {
        if (challengeList[0].type === 'error') {
          toast({
            title: challengeList[0].title || "Erro ao gerar desafio",
            description: challengeList[0].description || "Não foi possível gerar o desafio.",
            variant: "destructive",
          });
          setChallenges([]);
        } else {
          setChallenges(challengeList as Challenge[]);
          toast({
            title: `${challengeList.length} novos desafios gerados!`,
            description: `Desafios de ${selectedArea} carregados da API.`,
          });
        }
      } else {
        console.error("Resposta inesperada da API (esperava um array):", response);
        toast({
          title: "Erro inesperado",
          description: "A API retornou um formato desconhecido ou vazio.",
          variant: "destructive",
        });
        setChallenges([]);
      }
    } catch (error) {
      console.error("Falha ao gerar desafios:", error);
      toast({
        title: "Erro ao gerar desafios",
        description: "Não foi possível conectar à API ou ocorreu um erro no servidor.",
        variant: "destructive",
      });
      setChallenges([]);
    } finally {
      setIsLoading(false);
    }
  };

  // 3. TRANSFORMAR A FUNÇÃO EM ASYNC E IMPLEMENTAR A LÓGICA DE VALIDAÇÃO
  const handleSubmitAnswer = async (challengeId: string, answer: string) => {
    const currentChallenge = challenges[currentChallengeIndex];
    // Bloqueia nova submissão se uma já estiver em andamento
    if (!currentChallenge || currentChallenge.id !== challengeId || isSubmitting) return;

    setIsSubmitting(true); // Ativa o estado de "submetendo"

    try {
      // 4. CHAMAR A API DE VALIDAÇÃO REAL
      const validationResponse = await validateChallengeAnswer(currentChallenge, answer);
      const { is_correct, feedback } = validationResponse;

      // 5. ATUALIZAR O ESTADO COM O RESULTADO DA API
      setChallenges((prev) =>
        prev.map((c, index) => {
          if (index === currentChallengeIndex) {
            return {
              ...c,
              userAnswer: answer,
              isCorrect: is_correct,
              completed: is_correct, // Só marca como 'completed' se a resposta for correta
              feedback: feedback, // Armazena o feedback no objeto do desafio
            };
          }
          return c;
        })
      );

      // 6. MOSTRAR O TOAST COM O FEEDBACK REAL DA API
      toast({
        title: is_correct ? "Resposta Correta!" : "Resposta Incorreta.",
        description: feedback, // Usa o feedback vindo do Agente de Validação
        variant: is_correct ? "default" : "destructive",
      });

    } catch (error) {
      console.error("Falha ao validar resposta:", error);
      toast({
        title: "Erro ao validar",
        description: "Não foi possível conectar ao agente de validação. Tente novamente.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false); // Desativa o estado de "submetendo"
    }
  };

  // ... (Funções de navegação e getAreaName não mudam) ...
  const goToPreviousChallenge = () => {
    setCurrentChallengeIndex((prevIndex) => Math.max(0, prevIndex - 1));
  };

  const goToNextChallenge = () => {
    setCurrentChallengeIndex((prevIndex) => Math.min(challenges.length, prevIndex + 1));
  };
  
  const isLastChallenge = currentChallengeIndex === challenges.length - 1;

  const getAreaName = (area: string) => {
    const areaNames: Record<string, string> = {
      python: "Python",
      cpp: "C++",
      syna: "Syna",
      "dog-feeder": "Alimentador de Cachorros",
      "smart-garden": "Jardim Inteligente",
    };
    return areaNames[area] || area;
  };


  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-background to-muted/20">
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10">
        {/* ... (Header sem alteração) ... */}
        <div className="container px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                Desafios de Aprendizado
              </h1>
              <p className="text-sm text-muted-foreground">
                Área: {getAreaName(selectedArea)}
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => navigate("/area-selection")}>
                <Settings className="h-4 w-4 mr-2" />
                Mudar Área
              </Button>
              <Button onClick={generateNewChallenges} disabled={isLoading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
                Gerar Novos Desafios
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-auto">
        <div className="container py-8 px-4">
          {isLoading ? (
            <div className="flex justify-center">
              <Skeleton className="h-80 w-full max-w-2xl rounded-lg" />
            </div>
          ) : challenges.length > 0 && currentChallengeIndex < challenges.length ? (
            <div className="max-w-2xl mx-auto">
              <ChallengeCard
                key={challenges[currentChallengeIndex].id}
                challenge={challenges[currentChallengeIndex]}
                onSubmit={handleSubmitAnswer}
                // 7. PASSAR O ESTADO PARA O CARD (para desabilitar o botão)
                isSubmitting={isSubmitting} 
              />
              
              {/* ... (Botões de navegação sem alteração) ... */}
              <div className="flex justify-between mt-6">
                <Button 
                  onClick={goToPreviousChallenge} 
                  disabled={currentChallengeIndex === 0}
                  variant="outline"
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Anterior
                </Button>
                
                <Button 
                  onClick={goToNextChallenge}
                  variant="default"
                >
                  {isLastChallenge ? 'Finalizar' : 'Próximo'}
                  {isLastChallenge ? <CheckCircle2 className="h-4 w-4 ml-2" /> : <ArrowRight className="h-4 w-4 ml-2" />}
                </Button>
              </div>
            </div>
          ) : challenges.length > 0 && currentChallengeIndex >= challenges.length ? (
            // ... (Mensagem de conclusão sem alteração) ...
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <p className="text-xl font-semibold mb-4">Parabéns!</p>
              <p className="text-muted-foreground mb-4">
                Você completou todos os desafios de "{getAreaName(selectedArea)}".
              </p>
              <Button onClick={generateNewChallenges} disabled={isLoading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
                Gerar Novos Desafios
              </Button>
            </div>
          ) : (
            // ... (Mensagem inicial sem alteração) ...
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <p className="text-muted-foreground mb-4">
                Nenhum desafio disponível para "{getAreaName(selectedArea)}". Clique em "Gerar Novos Desafios" para começar!
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}