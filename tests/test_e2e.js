import { browser } from 'k6/browser';
import { check } from 'https://jslib.k6.io/k6-utils/1.5.0/index.js';
import { sleep } from 'k6';
import { open } from 'k6/experimental/fs';
import encoding from 'k6/encoding';

console.log("SCRIPT_LOG: Contexto de inicialización comenzando.");

// Función para leer el contenido de un archivo ya abierto y luego cerrarlo
async function readOpenedFileContent(fileHandle) {
  if (!fileHandle) {
    console.error("SCRIPT_LOG_ERROR: readOpenedFileContent fue llamado con un fileHandle nulo.");
    throw new Error("El manejador de archivo es nulo. El archivo no se pudo abrir en el contexto de inicialización.");
  }
  try {
    console.log("SCRIPT_LOG: Leyendo estadísticas del archivo...");
    const fileInfo = await fileHandle.stat();
    console.log(`SCRIPT_LOG: Estadísticas obtenidas: tamaño ${fileInfo.size}`);
    const buffer = new Uint8Array(fileInfo.size);
    console.log("SCRIPT_LOG: Leyendo contenido del archivo...");
    const bytesRead = await fileHandle.read(buffer);
    console.log(`SCRIPT_LOG: Bytes leídos: ${bytesRead}`);
    if (bytesRead !== fileInfo.size) {
      throw new Error(`Error al leer el archivo: se leyeron ${bytesRead} bytes de ${fileInfo.size}`);
    }
    return buffer.buffer; // Devuelve el ArrayBuffer subyacente
  } catch (e) {
    console.error(`SCRIPT_LOG_ERROR: Error en readOpenedFileContent: ${e.name} - ${e.message}`);
    throw e; // Relanzar el error para que sea visible
  } finally {
    if (fileHandle && typeof fileHandle.close === 'function') {
      try {
        console.log("SCRIPT_LOG: Intentando cerrar el archivo...");
        await fileHandle.close(); // Cerrar el archivo después de leerlo o en caso de error previo
        console.log("SCRIPT_LOG: Archivo cerrado exitosamente.");
      } catch (closeError) {
        console.error(`SCRIPT_LOG_ERROR: Error al cerrar el archivo: ${closeError.name} - ${closeError.message}`);
      }
    }
  }
}

// Abrir el archivo en el contexto de inicialización.
// Usamos una ruta absoluta para asegurar que k6 pueda encontrarlo.
const restauranteFilePath = 'D:/UMA/UMA_CODE/3/2cuatri/MPS/TicketSplitter/tests/images/restaurante.jpg';
let restauranteFilePromise = null;

console.log("SCRIPT_LOG: Configurando la promesa para abrir el archivo en el contexto de inicialización...");
try {
  restauranteFilePromise = (async () => {
    console.log(`SCRIPT_LOG: IIAFE iniciada para ${restauranteFilePath}.`);
    try {
      console.log(`SCRIPT_LOG: Intentando llamar a open() para ${restauranteFilePath}`);
      const file = await open(restauranteFilePath, 'r');
      console.log(`SCRIPT_LOG: open() exitoso para ${restauranteFilePath}. File object: ${typeof file}`);
      return file;
    } catch (e) {
      console.error(`SCRIPT_LOG_ERROR: IIAFE catch: Error en open() para ${restauranteFilePath}. Tipo: ${e.name}, Msg: ${e.message}`);
      console.error(`SCRIPT_LOG_ERROR_STACK: ${e.stack || 'No stack available'}`);
      return null;
    }
  })();
  console.log("SCRIPT_LOG: Promesa para open() configurada exitosamente.");
} catch (syncError) {
  console.error(`SCRIPT_LOG_ERROR: Error síncrono durante la configuración de la IIAFE: ${syncError.name} - ${syncError.message}`);
  restauranteFilePromise = Promise.resolve(null);
}

// Configuración de opciones
export const options = {
    scenarios: {
        browser: {
            executor: 'shared-iterations',
            vus: 1,
            iterations: 1,
            options: {
                browser: {
                    type: 'chromium',
                    headless: false
                }
            }
        }
    },
    thresholds: {
        http_req_duration: ['p(95)<500'], // 95% de las peticiones deben completarse en menos de 500ms
        http_req_failed: ['rate<0.01'], // Menos del 1% de las peticiones pueden fallar
    },
};

// Función principal de prueba
export default async function () {
    const page = await browser.newPage();
    try {
        // Navegar a la página principal
        await page.goto('http://localhost:4321');
        sleep(2);

        // Esperar a que el área de drop esté presente
        console.log('Esperando a que el área de drop esté presente...');
        await page.waitForSelector('.border-dashed');
        sleep(1);

        // Buscar el input de archivo por id
        console.log('Buscando input de archivo por id...');
        let fileInput = await page.$('#receipt-image');
        if (!fileInput) {
            console.log('No se encontró el input con id receipt-image. Buscando todos los inputs file...');
            // Imprimir todos los inputs file del DOM
            const allInputs = await page.evaluate(() => {
                return Array.from(document.querySelectorAll('input[type="file"]')).map(i => ({
                    id: i.id,
                    class: i.className,
                    name: i.name
                }));
            });
            console.log('Inputs file encontrados:', JSON.stringify(allInputs));
            throw new Error('No se encontró el input de archivo');
        }

        // Establecer el valor del input directamente usando setInputFiles
        console.log('Estableciendo el valor del input con setInputFiles para restaurante.jpg...');
        
        const restauranteFile = await restauranteFilePromise; // Esperar a que la promesa del archivo se resuelva
        if (!restauranteFile) {
            throw new Error(`No se pudo obtener el manejador para el archivo ${restauranteFilePath}. Revisa los logs del init context.`);
        }

        const restauranteBuffer = await readOpenedFileContent(restauranteFile);
        
        await fileInput.setInputFiles({
            name: 'restaurante.jpg',
            mimetype: 'image/jpeg',
            buffer: encoding.b64encode(restauranteBuffer),
        });
        
        console.log('Archivo seleccionado. Esperando 5 segundos para que la UI procese la imagen...');
        sleep(5); // Pausa generosa para que la UI se actualice después de la subida de la imagen

        // Buscar el botón "Subir y procesar"
        console.log('Buscando el botón "Subir y procesar"...');
        const allButtons = await page.$$('button');
        let subirBtnHandle = null;
        for (const btnHandle of allButtons) {
            const text = await btnHandle.textContent();
            if (text && text.includes('Subir y procesar')) {
                subirBtnHandle = btnHandle;
                break;
            }
        }

        if (!subirBtnHandle) { 
            console.error('CRITICAL: No se encontró el botón "Subir y procesar" tras iterar todos los botones.');
            await page.screenshot({ path: 'debug_no_subir_btn.png' });
            throw new Error('No se encontró el botón "Subir y procesar"');
        }
        
        console.log('Botón "Subir y procesar" encontrado. Intentando hacer clic...');
        try {
            await subirBtnHandle.click({ force: true, timeout: 10000 }); 
            console.log('Botón "Subir y procesar" clicado exitosamente (con force=true).');
        } catch (clickError) {
            console.warn(`Primer intento de clic (con force=true) falló: ${clickError.message}. Reintentando tras una breve pausa...`);
            await page.screenshot({ path: 'debug_primer_clic_forzado_fallido.png' });
            sleep(2); 
            try {
                await subirBtnHandle.scrollIntoViewIfNeeded(); 
                await subirBtnHandle.click({ force: true, timeout: 10000 });
                console.log('Botón "Subir y procesar" clicado exitosamente en el segundo intento (con force=true).');
            } catch (secondClickError) {
                console.error(`ERROR CRÍTICO al hacer clic en el botón "Subir y procesar" en el segundo intento (con force=true): ${secondClickError.message}`);
                console.error(`Stack del error de clic (segundo intento, forzado): ${secondClickError.stack || 'No stack available'}`);
                await page.screenshot({ path: 'debug_segundo_clic_forzado_fallido.png' });
                throw secondClickError; 
            }
        }
        
        console.log('Esperando 3 segundos después del clic para la carga del siguiente estado...');
        sleep(3); 

        // Verificar que el ticket se procesó correctamente
        await check(page.locator('body'), {
            'ticket restaurante procesado': async (lo) => {
                const content = await lo.textContent();
                return content.includes('Café con leche') && 
                       content.includes('Tostada integral') &&
                       content.includes('Zumo naranja natural') &&
                       content.includes('Croissant mantequilla');
            }
        });

        // Verificar los totales
        await check(page.locator('body'), {
            'totales correctos restaurante': async (lo) => {
                const content = await lo.textContent();
                return content.includes('12.40') && // subtotal
                       content.includes('1.24') &&  // tax
                       content.includes('13.64');   // total
            }
        });

        sleep(2);

    } finally {
        await page.close();
    }
} 