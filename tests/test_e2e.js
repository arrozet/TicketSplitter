import { browser } from 'k6/browser';
import { check } from 'https://jslib.k6.io/k6-utils/1.5.0/index.js';
import { sleep } from 'k6';
import { open } from 'k6/experimental/fs';
import encoding from 'k6/encoding';

// Función para leer el contenido completo de un archivo en un ArrayBuffer
async function readAll(filePath) {
  const file = await open(filePath, 'r'); // Abre el archivo en modo lectura
  const fileInfo = await file.stat();
  const buffer = new Uint8Array(fileInfo.size);
  const bytesRead = await file.read(buffer);
  if (bytesRead !== fileInfo.size) {
    throw new Error(`Error al leer el archivo ${filePath}: se leyeron ${bytesRead} bytes de ${fileInfo.size}`);
  }
  // file.close(); // Comentado temporalmente, k6 podría manejar el cierre automáticamente o necesitarlo en otro lugar.
                 // Si hay fugas de descriptores de archivo, se puede descomentar.
  return buffer.buffer; // Devuelve el ArrayBuffer subyacente
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
        const restaurantePath = 'D:/UMA/UMA_CODE/3/2cuatri/MPS/TicketSplitter/tests/images/restaurante.jpg';
        const restauranteBuffer = await readAll(restaurantePath);
        await fileInput.setInputFiles({
            name: 'restaurante.jpg',
            mimeType: 'image/jpeg',
            buffer: encoding.b64encode(restauranteBuffer),
        });
        
        console.log('Archivo seleccionado. Esperando 2 segundos...');
        sleep(2);

        // Buscar y comprobar el botón "Subir y procesar"
        const procesarBtns = await page.$$('button');
        let subirBtn = null;
        for (const btn of procesarBtns) {
            const text = await btn.textContent();
            if (text && text.includes('Subir y procesar')) {
                subirBtn = btn;
                break;
            }
        }
        if (!subirBtn) {
            console.log('No se encontró el botón Subir y procesar');
            throw new Error('No se encontró el botón Subir y procesar');
        }
        const btnDisabled = await subirBtn.evaluate(btn => btn.disabled);
        console.log('Botón Subir y procesar encontrado. ¿Está deshabilitado?:', btnDisabled);
        sleep(2);

        // Hacer clic en el botón si está habilitado
        if (!btnDisabled) {
            await subirBtn.click();
            console.log('Botón Subir y procesar clicado.');
        } else {
            console.log('El botón Subir y procesar está deshabilitado. No se puede clicar.');
        }
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