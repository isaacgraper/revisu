import FileProcessor from "@/components/FileProcessor";
import LatestFilesList from "@/components/LatestFilesList";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gray-100 dark:bg-gray-900">
      <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-10">
        Revisu - Sua Ferramenta de Revisão Espaçada
      </h1>

      <div className="flex flex-col md:flex-row gap-8 w-full max-w-5xl">
        <div className="md:w-1/2 flex justify-center">
          <FileProcessor />
        </div>
        <div className="md:w-1/2 flex justify-center">
          <LatestFilesList />
        </div>
      </div>
    </main>
  );
}
