"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

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

interface ProcessedFile {
  id: number;
  file_path: string;
  file_name: string;
  file_type: string;
  processed_at: string;
  topics: ProcessedTopic[];
}

export default function FileDetailsPage() {
  const { fileId } = useParams<{ fileId: string }>();
  const [fileDetails, setFileDetails] = useState<ProcessedFile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (!fileId) return;

    const fetchFileDetails = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const response = await axios.get<ProcessedFile>(
          `${API_BASE_URL}/files/${fileId}`,
        );
        setFileDetails(response.data);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response) {
          setError(
            `Erro ao carregar detalhes do arquivo: ${err.response.status} - ${err.response.data.detail || err.message}`,
          );
        } else {
          setError(
            `Ocorreu um erro inesperado: ${err instanceof Error ? err.message : String(err)}`,
          );
        }
        console.error("Erro ao carregar detalhes do arquivo:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchFileDetails();
  }, [fileId, API_BASE_URL]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen text-xl">
        Carregando detalhes do arquivo...
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

  if (!fileDetails) {
    return (
      <div className="flex justify-center items-center h-screen text-gray-500 text-xl">
        Arquivo não encontrado.
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <Button onClick={() => router.push("/files")} className="mb-6">
        Voltar para todos os arquivos
      </Button>
      <h1 className="text-3xl font-bold mb-4 text-center">
        Detalhes do Arquivo: {fileDetails.file_name}
      </h1>
      <p className="text-lg text-gray-700 dark:text-gray-300 text-center mb-6">
        Processado em: {new Date(fileDetails.processed_at).toLocaleString()}
      </p>

      <h2 className="text-2xl font-semibold mb-4">
        Tópicos ({fileDetails.topics.length})
      </h2>
      {fileDetails.topics.length === 0 ? (
        <p className="text-gray-500">
          Nenhum tópico encontrado para este arquivo.
        </p>
      ) : (
        <div className="space-y-6">
          {fileDetails.topics.map((topic) => (
            <div
              key={topic.id}
              className="p-5 border rounded-lg shadow-md bg-white dark:bg-gray-800"
            >
              <h3 className="text-xl font-bold mb-2">
                {topic.title || "Tópico Sem Título"}
              </h3>
              <p className="text-gray-700 dark:text-gray-200 mb-3">
                {topic.summary}
              </p>

              <p className="font-medium text-lg mt-4">
                Perguntas para Revisão:
              </p>
              <ul className="list-disc list-inside text-gray-600 dark:text-gray-300 mb-3">
                {topic.questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>

              {topic.tags && topic.tags.length > 0 && (
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                  Tags:{" "}
                  <span className="font-semibold">{topic.tags.join(", ")}</span>
                </p>
              )}
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Próxima Revisão:{" "}
                <span className="font-semibold">
                  {new Date(topic.next_review_date).toLocaleDateString()}
                </span>
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Fator de Facilidade (EF):{" "}
                <span className="font-semibold">
                  {topic.ease_factor.toFixed(2)}
                </span>
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Repetições:{" "}
                <span className="font-semibold">{topic.repetitions}</span>
              </p>
              {topic.last_reviewed && (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Última Revisão:{" "}
                  <span className="font-semibold">
                    {new Date(topic.last_reviewed).toLocaleDateString()}
                  </span>
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
