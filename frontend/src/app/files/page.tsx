"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
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

export default function FilesPage() {
  const [files, setFiles] = useState<ProcessedFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const fetchFiles = async () => {
      try {
        const response = await axios.get<ProcessedFile[]>(
          `${API_BASE_URL}/files`,
        );
        console.log(response.data);
        setFiles(response.data);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response) {
          setError(
            `Erro ao carregar arquivos: ${err.response.status} - ${err.response.data.detail || err.message}`,
          );
        } else {
          setError(
            `Ocorreu um erro inesperado: ${err instanceof Error ? err.message : String(err)}`,
          );
        }
        console.error("Error loading files:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchFiles();
  }, [API_BASE_URL]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen text-xl">
        Carregando arquivos...
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

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6 text-center">
        Todos os Arquivos Processados
      </h1>
      <div className="flex justify-center mb-6">
        <Button onClick={() => router.push("/")}>Processar Novo Arquivo</Button>
        <Button
          onClick={() => router.push("/review")}
          className="bg-green-500 hover:bg-green-600 text-white"
        >
          Iniciar Revisão Agora
        </Button>
      </div>

      {files.length === 0 ? (
        <p className="text-center text-gray-500 text-lg">
          Nenhum arquivo processado ainda. Comece processando um!
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {files.map((file) => (
            <div
              key={file.id}
              className="border rounded-lg shadow-md p-5 bg-white dark:bg-gray-800"
            >
              <h2 className="text-xl font-semibold mb-2 truncate">
                {file.file_name}
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Tipo: {file.file_type.toUpperCase()}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
                Processado em:{" "}
                {new Date(file.processed_at).toLocaleDateString()}
              </p>
              <h3 className="text-lg font-medium mt-4">
                Tópicos ({file.topics.length})
              </h3>
              <ul className="list-disc list-inside text-sm text-gray-700 dark:text-gray-200">
                {file.topics.slice(0, 3).map((topic) => (
                  <li key={topic.id} className="truncate">
                    {topic.title || topic.summary.substring(0, 30) + "..."}
                  </li>
                ))}
                {file.topics.length > 3 && (
                  <li className="text-gray-500">
                    e mais {file.topics.length - 3} tópicos...
                  </li>
                )}
              </ul>
              <Button
                onClick={() => router.push(`/files/${file.id}`)}
                className="mt-4 w-full"
              >
                Ver Detalhes
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
