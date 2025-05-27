"use client";

import React, { useState, ChangeEvent } from "react";
import axios from "axios";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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

export default function FileProcessor() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingFileName, setProcessingFileName] = useState<string | null>(
    null,
  );

  const router = useRouter();
  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setSelectedFile(event.target.files[0]);
      setError(null);
    }
  };

  const handleProcessFile = async () => {
    if (!selectedFile) {
      setError("Please, select a file to process.");
      return;
    }

    setIsLoading(true);
    setProcessingFileName(selectedFile.name);
    setError(null);

    const formData = new FormData();

    formData.append("file", selectedFile);

    formData.append(
      "file_type",
      selectedFile.name.split(".").pop() || "unknown",
    );

    try {
      const response = await axios.post<ProcessedFile>(
        `${API_BASE_URL}/files/process`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        },
      );

      console.log("File processed successfully:", response.data);
      router.push(`/files/${response.data.id}`);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        const errorDetail = err.response.data.detail
          ? JSON.stringify(err.response.data.detail, null, 2)
          : err.message;

        setError(`Error while processing file: ${errorDetail}`);
        console.error("Error:", err.response.data);
      } else {
        setError(
          `An error occurred: ${err instanceof Error ? err.message : String(err)}`,
        );
      }
      console.error("Error while processing file:", err);
    } finally {
      setIsLoading(false);
      setSelectedFile(null);
      const fileInput = document.getElementById(
        "file-upload-input",
      ) as HTMLInputElement;
      if (fileInput) {
        fileInput.value = "";
      }
    }
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col justify-center items-center bg-gray-50 dark:bg-gray-900 text-gray-700 dark:text-gray-300">
        <svg
          className="animate-spin h-12 w-12 text-blue-500 mb-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
        <p className="text-xl font-semibold mb-2">Processando arquivo...</p>
        {processingFileName && <p className="text-lg">{processingFileName}</p>}
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
          Isso pode levar alguns instantes.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center p-6 border rounded-lg shadow-lg bg-white dark:bg-gray-800 w-full max-w-md">
      <h2 className="text-2xl font-semibold mb-4 text-center">
        Processar Novo Arquivo
      </h2>

      <div className="w-full mb-4">
        <Input
          type="file"
          id="file-upload-input"
          accept=".md"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-500
                     file:mr-4 file:py-2 file:px-4
                     file:rounded-full file:border-0
                     file:text-sm file:font-semibold
                     file:bg-blue-50 file:text-blue-700
                     hover:file:bg-blue-100 dark:file:bg-blue-900
                     dark:file:text-blue-100 dark:hover:file:bg-blue-800"
        />
        {selectedFile && (
          <p className="text-sm mt-2 text-gray-600 dark:text-gray-300">
            Arquivo selecionado:{" "}
            <span className="font-medium">{selectedFile.name}</span>
          </p>
        )}
      </div>

      <Button
        onClick={handleProcessFile}
        disabled={isLoading || !selectedFile}
        className="w-full py-2 px-4 rounded-md text-lg"
      >
        Processar Arquivo
      </Button>

      {error && (
        <p className="text-red-500 text-sm mt-4 text-center">{error}</p>
      )}
    </div>
  );
}
