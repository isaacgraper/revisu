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

export default function LatestFilesList() {
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
          `${API_BASE_URL}/files?limit=5`,
        );
        setFiles(response.data);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response) {
          setError(
            `Erro ao carregar arquivos: ${err.response.status} - ${
              err.response.data.detail || err.message
            }`,
          );
        } else {
          setError(
            `Ocorreu um erro inesperado: ${
              err instanceof Error ? err.message : String(err)
            }`,
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
      <div className="flex justify-center items-center h-24 text-gray-500">
        Carregando últimas notas...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-24 text-red-500 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="w-full max-w-lg p-6 border rounded-lg shadow-lg bg-white dark:bg-gray-800">
      <h2 className="text-2xl font-semibold mb-4 text-center">
        Últimas Notas Processadas
      </h2>

      {files.length === 0 ? (
        <p className="text-center text-gray-500 text-base">
          Nenhuma nota processada ainda.
        </p>
      ) : (
        <div className="space-y-4">
          {files.map((file) => (
            <div
              key={file.id}
              className="p-3 border rounded-md bg-gray-50 dark:bg-gray-700"
            >
              <h3 className="font-semibold text-lg truncate">
                {file.file_name}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Tópicos: {file.topics.length}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Processado em:{" "}
                {new Date(file.processed_at).toLocaleDateString()}
              </p>
              <Button
                variant="link"
                onClick={() => router.push(`/files/${file.id}`)}
                className="p-0 h-auto text-blue-600 dark:text-blue-400"
              >
                Ver Detalhes
              </Button>
            </div>
          ))}
        </div>
      )}
      <Button
        onClick={() => router.push("/files")}
        className="mt-6 w-full py-2 px-4 rounded-md text-lg"
      >
        Ver Todas as Notas
      </Button>
    </div>
  );
}
