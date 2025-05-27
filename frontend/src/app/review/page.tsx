"use client";

import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useRouter } from "next/navigation";

interface ProcessedTopic {
  id: number;
  file_id: number;
  title: string | null;
  summary: string;
  questions: string[];
  next_review_date: string;
  ease_factor: number;
  repetitions: number;
  last_reviewed: string | null;
  tags: string[];
}

export default function ReviewPage() {
  const router = useRouter();
  const [topics, setTopics] = useState<ProcessedTopic[]>([]);
  const [currentTopicIndex, setCurrentTopicIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [showAnswer, setShowAnswer] = useState(false);

  const [reviewedCount, setReviewedCount] = useState(0);
  const [initialTotalTopics, setInitialTotalTopics] = useState(0);

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchTopicsForReview = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setMessage(null);

    try {
      const response = await axios.get<ProcessedTopic[]>(
        `${API_BASE_URL}/topics/for-review`,
      );

      setTopics(response.data);
      setInitialTotalTopics(response.data.length);
      setReviewedCount(0);
      setCurrentTopicIndex(0);
      setShowAnswer(false);

      if (response.data.length === 0) {
        setMessage(
          "🎉 Nenhum tópico para revisar no momento! Volte mais tarde.",
        );
      }
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        setError(
          `Erro ao carregar tópicos: ${err.response.status} - ${err.response.data.detail || err.message}`,
        );
      } else {
        setError(
          `Ocorreu um erro inesperado: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
      console.error("Error loading topics for review:", err);
    } finally {
      setIsLoading(false);
    }
  }, [API_BASE_URL]);

  useEffect(() => {
    fetchTopicsForReview();
  }, [fetchTopicsForReview]);

  const handleReview = async (quality: number) => {
    if (!topics[currentTopicIndex]) return;

    const topicId = topics[currentTopicIndex].id;
    setMessage(
      `Registrando revisão para "${topics[currentTopicIndex].title}"...`,
    );

    try {
      await axios.post(`${API_BASE_URL}/topics/${topicId}/review`, { quality });
      setMessage("Revisão registrada com sucesso!");
      setReviewedCount((prev) => prev + 1);

      const updatedTopics = topics.filter(
        (_, idx) => idx !== currentTopicIndex,
      );
      setTopics(updatedTopics);

      setShowAnswer(false);

      if (updatedTopics.length > 0) {
        if (currentTopicIndex >= updatedTopics.length) {
          setCurrentTopicIndex(0);
        }
      } else {
        setMessage("✅ Sessão de revisão concluída! Redirecionando...");
        setTimeout(() => {
          router.push("/files");
        }, 3000);
      }
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        setError(
          `Erro ao registrar revisão: ${err.response.status} - ${err.response.data.detail || err.message}`,
        );
      } else {
        setError(
          `Ocorreu um erro inesperado ao revisar: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
      console.error("Error reviewing topic:", err);
    }
  };

  const handleSkip = () => {
    if (!topics[currentTopicIndex]) return;

    setMessage("Tópico pulado e concluído para esta sessão.");
    setReviewedCount((prev) => prev + 1);

    const updatedTopics = topics.filter((_, idx) => idx !== currentTopicIndex);
    setTopics(updatedTopics);

    setShowAnswer(false);

    if (updatedTopics.length > 0) {
      if (currentTopicIndex >= updatedTopics.length) {
        setCurrentTopicIndex(0);
      }
    } else {
      setMessage(
        "✅ Sessão de revisão concluída (tópicos restantes pulados)! Redirecionando...",
      );
      setTimeout(() => {
        router.push("/files");
      }, 3000);
    }
  };

  const currentTopic = topics[currentTopicIndex];

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen text-xl">
        Carregando tópicos para revisão...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-screen text-red-500 text-xl">
        {error}
      </div>
    );
  }

  const progressPercentage =
    initialTotalTopics > 0 ? (reviewedCount / initialTotalTopics) * 100 : 0;

  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <h1 className="text-3xl font-bold mb-6 text-center">Revisar Tópicos</h1>

      {initialTotalTopics > 0 && (
        <div className="text-center mb-4 text-gray-700 dark:text-gray-300">
          Progresso: {reviewedCount} de {initialTotalTopics} tópicos revisados
          <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 mt-2">
            <div
              className="bg-blue-600 h-2.5 rounded-full"
              style={{ width: `${progressPercentage}%` }}
            ></div>
          </div>
        </div>
      )}

      {message && (
        <div
          className="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded relative mb-4"
          role="alert"
        >
          <span className="block sm:inline">{message}</span>
        </div>
      )}

      {topics.length === 0 && !isLoading && !error ? (
        <div className="text-center text-gray-600 text-lg">
          <p>🎉 Nenhum tópico para revisar no momento!</p>
          <p className="mt-2">
            Continue aprendendo e novos tópicos aparecerão para você em breve.
          </p>
          <Button onClick={() => fetchTopicsForReview()} className="mt-4">
            Atualizar Tópicos
          </Button>
          <Button onClick={() => router.push("/files")} className="mt-4 ml-2">
            Ver Todos os Arquivos
          </Button>
        </div>
      ) : (
        currentTopic && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>{currentTopic.title}</CardTitle>
              <CardDescription>
                Próxima revisão agendada para:{" "}
                {new Date(currentTopic.next_review_date).toLocaleDateString()}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4">{currentTopic.summary}</p>

              {currentTopic.tags && currentTopic.tags.length > 0 && (
                <div className="mb-4">
                  {currentTopic.tags.map((tag, idx) => (
                    <Badge key={idx} variant="secondary" className="mr-2 mb-1">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}

              <Button
                onClick={() => setShowAnswer(!showAnswer)}
                className="mb-4"
              >
                {showAnswer ? "Esconder Perguntas" : "Mostrar Perguntas"}
              </Button>

              {showAnswer && (
                <div className="mt-4 border-t pt-4">
                  <h3 className="text-lg font-semibold mb-2">
                    Perguntas para Reflexão:
                  </h3>
                  <ul className="list-disc pl-5">
                    {currentTopic.questions.length > 0 ? (
                      currentTopic.questions.map((q, idx) => (
                        <li key={idx} className="mb-1">
                          {q}
                        </li>
                      ))
                    ) : (
                      <li>Nenhuma pergunta disponível para este tópico.</li>
                    )}
                  </ul>
                </div>
              )}
            </CardContent>
            <CardFooter className="flex flex-col items-start pt-4 border-t mt-4">
              <p className="font-semibold mb-2">
                Qualidade da Lembrança (0=Esqueci, 5=Perfeito):
              </p>
              <div className="flex gap-2 flex-wrap">
                {[0, 1, 2, 3, 4, 5].map((quality) => (
                  <Button
                    key={quality}
                    onClick={() => handleReview(quality)}
                    disabled={isLoading}
                    variant={
                      quality < 3
                        ? "destructive"
                        : quality < 5
                          ? "default"
                          : "secondary"
                    }
                    className={
                      quality === 5
                        ? "bg-green-500 hover:bg-green-600 text-white"
                        : ""
                    }
                  >
                    {quality}
                  </Button>
                ))}
                <Button
                  onClick={handleSkip}
                  disabled={isLoading}
                  variant="outline"
                  className="ml-4"
                >
                  Pular Tópico
                </Button>
              </div>
            </CardFooter>
          </Card>
        )
      )}
    </div>
  );
}
