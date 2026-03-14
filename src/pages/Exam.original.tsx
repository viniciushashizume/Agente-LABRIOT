import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, CheckCircle2, XCircle, Loader2, Clock, AlertTriangle, History } from "lucide-react";
import { Challenge } from "@/types/challenge";
import { generateChallenges, validateChallengeAnswer, ValidationApiResponse } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface ExamHistory {
  id: string;
  date: string;
  score: number;
  total: number;
  percentage: number;
  timeSpent: number;
}

export default function Exam() {
  const navigate = useNavigate();
  const { toast } = useToast();

  // Tempo limite em segundos (30 minutos = 1800 segundos)
  const EXAM_TIME_LIMIT = 1800;

  const [isLoadingExam, setIsLoadingExam] = useState(false);
  const [isSubmittingExam, setIsSubmittingExam] = useState(false);
  const [examStarted, setExamStarted] = useState(false);
  const [examFinished, setExamFinished] = useState(false);
  const [questions, setQuestions] = useState<Challenge[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [validationResults, setValidationResults] = useState<Record<number, ValidationApiResponse>>({});
  const [timeRemaining, setTimeRemaining] = useState(EXAM_TIME_LIMIT);
  const [examHistory, setExamHistory] = useState<ExamHistory[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const examStartTime = useRef<number>(0);

  // Load exam history from localStorage
  useEffect(() => {
    const savedHistory = localStorage.getItem("examHistory");
    if (savedHistory) {
      setExamHistory(JSON.parse(savedHistory));
    }
  }, []);

  // Timer effect
  useEffect(() => {
    if (examStarted && !examFinished && timeRemaining > 0) {
      timerRef.current = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            // Tempo esgotado - submeter automaticamente
            clearInterval(timerRef.current!);
            toast({
              title: "Tempo Esgotado!",
              description: "A prova será submetida automaticamente.",
              variant: "destructive",
            });
            submitExam();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      return () => {
        if (timerRef.current) {
          clearInterval(timerRef.current);
        }
      };
    }
  }, [examStarted, examFinished, timeRemaining]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const getTimeColor = () => {
    if (timeRemaining <= 60) return "text-destructive";
    if (timeRemaining <= 300) return "text-yellow-600 dark:text-yellow-500";
    return "text-muted-foreground";
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

const startExam = async () => {
    setIsLoadingExam(true);
    try {
      // Gera desafios sobre conteúdos gerais do projeto
      // <<< MODIFICADO: Passando 10 como segundo argumento >>>
      const response = await generateChallenges("conteúdos gerais do projeto", 10);
      
      if (response.challenges && response.challenges.length > 0) {
        setQuestions(response.challenges);
        setExamStarted(true);
        setCurrentQuestion(0);
        setTimeRemaining(EXAM_TIME_LIMIT);
        examStartTime.current = Date.now();
      } else {
        toast({
          title: "Erro",
          description: "Não foi possível gerar a prova. Tente novamente.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Erro ao iniciar prova:", error);
      toast({
        title: "Erro",
        description: "Falha ao carregar a prova.",
        variant: "destructive",
      });
    } finally {
      setIsLoadingExam(false);
    }
  };

  const handleAnswerChange = (value: string) => {
    setAnswers({ ...answers, [currentQuestion]: value });
  };

  const goToNextQuestion = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    }
  };

  const goToPreviousQuestion = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
    }
  };

  const submitExam = async () => {
    setIsSubmittingExam(true);
    const results: Record<number, ValidationApiResponse> = {};

    try {
      for (let i = 0; i < questions.length; i++) {
        const question = questions[i];
        const userAnswer = answers[i] || "";
        
        try {
          const validation = await validateChallengeAnswer(question, userAnswer);
          results[i] = validation;
        } catch (error) {
          console.error(`Erro ao validar questão ${i}:`, error);
          results[i] = {
            is_correct: false,
            feedback: "Erro ao validar esta questão."
          };
        }
      }

      setValidationResults(results);
      setExamFinished(true);
      
      // Calculate score and save to history
      const correctCount = Object.values(results).filter(r => r.is_correct).length;
      const percentage = (correctCount / questions.length) * 100;
      const timeSpent = EXAM_TIME_LIMIT - timeRemaining;
      
      const newHistoryEntry: ExamHistory = {
        id: Date.now().toString(),
        date: new Date().toISOString(),
        score: correctCount,
        total: questions.length,
        percentage,
        timeSpent,
      };

      const updatedHistory = [newHistoryEntry, ...examHistory];
      setExamHistory(updatedHistory);
      localStorage.setItem("examHistory", JSON.stringify(updatedHistory));
      
      toast({
        title: "Prova Concluída!",
        description: "Confira seus resultados abaixo.",
      });
    } catch (error) {
      console.error("Erro ao submeter prova:", error);
      toast({
        title: "Erro",
        description: "Falha ao submeter a prova.",
        variant: "destructive",
      });
    } finally {
      setIsSubmittingExam(false);
    }
  };

  const getCorrectCount = () => {
    return Object.values(validationResults).filter((result) => result.is_correct).length;
  };

  const restartExam = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    setExamStarted(false);
    setExamFinished(false);
    setQuestions([]);
    setCurrentQuestion(0);
    setAnswers({});
    setValidationResults({});
    setTimeRemaining(EXAM_TIME_LIMIT);
  };

  // Exam Results View
  if (examFinished) {
    const correctCount = getCorrectCount();
    const totalQuestions = questions.length;
    const percentage = Math.round((correctCount / totalQuestions) * 100);

    return (
      <div className="container mx-auto p-6 max-w-4xl">
        <Button
          variant="ghost"
          onClick={restartExam}
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Nova Prova
        </Button>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Resultados da Prova</CardTitle>
            <CardDescription>Conteúdos Gerais do Projeto</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center mb-6">
              <div className="text-4xl font-bold mb-2">
                {correctCount} / {totalQuestions}
              </div>
              <div className="text-muted-foreground mb-4">
                Você acertou {percentage}% das questões
              </div>
              <Progress value={percentage} className="h-3" />
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {questions.map((question, index) => {
            const result = validationResults[index];
            const userAnswer = answers[index] || "Não respondida";

            return (
              <Card key={question.id} className="border-l-4" style={{
                borderLeftColor: result?.is_correct ? "hsl(var(--success))" : "hsl(var(--destructive))"
              }}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-lg flex items-center gap-2">
                        {result?.is_correct ? (
                          <CheckCircle2 className="h-5 w-5 text-green-600" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-600" />
                        )}
                        Questão {index + 1}
                      </CardTitle>
                      <CardDescription className="mt-2">{question.description}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <p className="font-semibold text-sm text-muted-foreground mb-1">Sua resposta:</p>
                    {question.type === "multiple-choice" && question.options ? (
                      <p className="text-sm">
                        {question.options.find(opt => opt.id === userAnswer)?.text || userAnswer}
                      </p>
                    ) : (
                      <p className="text-sm whitespace-pre-wrap bg-muted p-3 rounded-md">
                        {userAnswer}
                      </p>
                    )}
                  </div>

                  {result && (
                    <Alert variant={result.is_correct ? "default" : "destructive"}>
                      <AlertDescription className="text-sm">
                        <strong>Feedback:</strong> {result.feedback}
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="mt-6 flex justify-center">
          <Button onClick={restartExam} size="lg">
            Fazer Nova Prova
          </Button>
        </div>
      </div>
    );
  }

  // Exam in Progress View
  if (examStarted && questions.length > 0) {
    const question = questions[currentQuestion];
    const progress = ((currentQuestion + 1) / questions.length) * 100;

    return (
      <div className="container mx-auto p-6 max-w-3xl">
        {/* Timer Alert */}
        {timeRemaining <= 300 && (
          <Alert variant={timeRemaining <= 60 ? "destructive" : "default"} className="mb-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              {timeRemaining <= 60 
                ? "Atenção! Menos de 1 minuto restante!" 
                : "Atenção! Menos de 5 minutos restantes!"
              }
            </AlertDescription>
          </Alert>
        )}

        {/* Timer Display */}
        <Card className="mb-6 border-2">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className={`h-5 w-5 ${getTimeColor()}`} />
                <span className="text-sm font-medium">Tempo Restante</span>
              </div>
              <div className={`text-2xl font-bold tabular-nums ${getTimeColor()}`}>
                {formatTime(timeRemaining)}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm text-muted-foreground">
              Questão {currentQuestion + 1} de {questions.length}
            </span>
            <span className="text-sm font-medium">{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{question.title}</CardTitle>
            <CardDescription>{question.description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {question.type === "multiple-choice" && question.options ? (
              <RadioGroup
                value={answers[currentQuestion] || ""}
                onValueChange={handleAnswerChange}
              >
                {question.options.map((option) => (
                  <div key={option.id} className="flex items-center space-x-2">
                    <RadioGroupItem value={option.id} id={option.id} />
                    <Label htmlFor={option.id} className="cursor-pointer">
                      {option.text}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            ) : (
              <Textarea
                placeholder={
                  question.type === "code"
                    ? "Digite seu código aqui..."
                    : "Digite sua resposta aqui..."
                }
                value={answers[currentQuestion] || ""}
                onChange={(e) => handleAnswerChange(e.target.value)}
                className="min-h-[200px] font-mono"
              />
            )}
          </CardContent>
        </Card>

        <div className="flex justify-between mt-6">
          <Button
            variant="outline"
            onClick={goToPreviousQuestion}
            disabled={currentQuestion === 0}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Anterior
          </Button>

          {currentQuestion === questions.length - 1 ? (
            <Button
              onClick={submitExam}
              disabled={isSubmittingExam}
            >
              {isSubmittingExam ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Finalizando...
                </>
              ) : (
                "Finalizar Prova"
              )}
            </Button>
          ) : (
            <Button onClick={goToNextQuestion}>
              Próxima
              <ArrowLeft className="ml-2 h-4 w-4 rotate-180" />
            </Button>
          )}
        </div>
      </div>
    );
  }

  // Start Exam View
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <Button onClick={() => navigate("/")} variant="ghost" className="mb-6">
        <ArrowLeft className="mr-2 h-4 w-4" />
        Voltar
      </Button>
      
      <Tabs defaultValue="start" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="start">Iniciar Prova</TabsTrigger>
          <TabsTrigger value="history">
            <History className="mr-2 h-4 w-4" />
            Histórico
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="start">
          <Card>
            <CardHeader>
              <CardTitle>Prova de Conhecimentos Gerais</CardTitle>
              <CardDescription>
                Teste seus conhecimentos sobre os conteúdos do projeto. Você terá 30 minutos para completar a prova.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <h3 className="font-semibold">Instruções:</h3>
                <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                  <li>A prova contém questões objetivas e dissertativas</li>
                  <li>Você tem 30 minutos para completar todas as questões</li>
                  <li>Todas as respostas serão validadas automaticamente</li>
                  <li>Você pode navegar entre as questões livremente</li>
                  <li>Ao finalizar, você verá sua pontuação e feedback detalhado</li>
                </ul>
              </div>
              
              <Button 
                onClick={startExam} 
                className="w-full"
                disabled={isLoadingExam}
              >
                {isLoadingExam ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Carregando Prova...
                  </>
                ) : (
                  "Iniciar Prova"
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle>Histórico de Provas</CardTitle>
              <CardDescription>
                Veja o histórico das suas provas anteriores
              </CardDescription>
            </CardHeader>
            <CardContent>
              {examHistory.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Você ainda não realizou nenhuma prova.
                </div>
              ) : (
                <div className="space-y-3">
                  {examHistory.map((entry) => (
                    <Card key={entry.id} className="border-2">
                      <CardContent className="pt-6">
                        <div className="flex justify-between items-start">
                          <div className="space-y-1">
                            <p className="text-sm text-muted-foreground">
                              {formatDate(entry.date)}
                            </p>
                            <p className="font-semibold">
                              Pontuação: {entry.score}/{entry.total} ({entry.percentage.toFixed(1)}%)
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Tempo gasto: {formatTime(entry.timeSpent)}
                            </p>
                          </div>
                          <div className={`text-2xl font-bold ${
                            entry.percentage >= 70 ? "text-success" : "text-destructive"
                          }`}>
                            {entry.percentage >= 70 ? (
                              <CheckCircle2 className="h-8 w-8" />
                            ) : (
                              <XCircle className="h-8 w-8" />
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}