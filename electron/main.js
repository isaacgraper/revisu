const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs'); // Adicionar esta linha para usar fs.existsSync

let pythonProcess = null;

// Função para obter o caminho do executável do backend
const getBackendExecutablePath = () => {
  let backendExecutable;
  // Em desenvolvimento, o executável está na pasta 'backend/dist'
  // IMPORTANTE: Assumimos que 'electron' e 'backend' são irmãos na pasta raiz do projeto.
  // path.join(__dirname, '..', 'backend', 'dist', ...) navega um nível acima e depois para 'backend/dist'.
  if (process.platform === 'win32') {
    backendExecutable = path.join(__dirname, '..', 'backend', 'dist', 'fastapi_backend.exe');
  } else {
    // Linux e macOS não usam a extensão .exe
    backendExecutable = path.join(__dirname, '..', 'backend', 'dist', 'fastapi_backend');
  }
  return backendExecutable;
};

const startPythonBackend = () => {
  const backendExecutablePath = getBackendExecutablePath();

  console.log(`Tentando iniciar backend Python em: ${backendExecutablePath}`);

  if (!fs.existsSync(backendExecutablePath)) {
    console.error(`Erro: Executável do backend não encontrado em ${backendExecutablePath}. Você rodou 'pyinstaller' na pasta backend?`);
    // Pode mostrar uma mensagem de erro na UI aqui para o usuário
    return;
  }

  // Use spawn para iniciar o executável do backend
  pythonProcess = spawn(backendExecutablePath, [], { // Sem o 'python3', apenas o executável
    stdio: 'inherit', // Permite que a saída do Python apareça no terminal do Electron
    detached: false,  // Garante que o processo Python morra com o Electron
    cwd: path.join(__dirname, '..', 'backend'), // Define o diretório de trabalho para o backend, pode ser útil
  });

  pythonProcess.on('error', (err) => {
    console.error('Falha ao iniciar o backend Python:', err);
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`Backend Python encerrado com código ${code} e sinal ${signal}`);
    pythonProcess = null;
  });

  console.log('Backend Python iniciado.');
};

const stopPythonBackend = () => {
  if (pythonProcess) {
    console.log('Encerrando backend Python...');
    pythonProcess.kill();
  }
};

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      // preload: path.join(__dirname, 'preload.js'), // Vamos criar um preload básico depois
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  // Em desenvolvimento, carregue a URL do Next.js
  // Quando for empacotado, vamos carregar o build estático.
  if (app.isPackaged) {
    // Isso é para quando o aplicativo estiver empacotado.
    // O electron-builder precisará copiar a pasta de build do Next.js.
    // Vamos usar um placeholder por enquanto.
    // win.loadFile(path.join(__dirname, '..', 'frontend', 'out', 'index.html')); // Exemplo para build estático
    console.log('Modo empacotado: Carregando frontend do build...');
    // Para testar o build empacotado, você precisará configurar o electron-builder
    // e rodar o comando de package.
    // Por enquanto, em desenvolvimento, carregamos a URL.
     win.loadURL('http://localhost:3000'); // Mesmo em modo empacotado, se não houver build local
  } else {
    win.loadURL('http://localhost:3000'); // Em desenvolvimento
    win.webContents.openDevTools(); // Ferramentas de dev apenas em desenvolvimento
  }
}

app.whenReady().then(() => {
  startPythonBackend();
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', stopPythonBackend);

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
