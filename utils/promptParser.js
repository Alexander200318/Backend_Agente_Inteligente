// ============================================================
// 📁 UBICACIÓN: backend/utils/promptParser.js (NUEVO ARCHIVO)
// ============================================================

/**
 * Parsear prompt_sistema y extraer componentes individuales
 * @param {string} prompt_sistema - Prompt completo guardado en BD
 * @returns {object} Objeto con campos separados
 */
const parsePromptSistema = (prompt_sistema) => {
  if (!prompt_sistema || typeof prompt_sistema !== 'string') {
    return {
      prompt_mision: '',
      prompt_reglas: [],
      prompt_tono: 'amigable',
      prompt_especializado: '',
    };
  }

  let prompt_mision = '';
  let prompt_reglas = [];
  let prompt_tono = 'amigable';
  let prompt_especializado = '';

  try {
    // 1. Extraer MISIÓN
    const misionRegex = /MISIÓN:\s*\n([\s\S]*?)(?=\n\n(?:ESPECIALIZACIÓN|REGLAS|TONO)|$)/i;
    const misionMatch = prompt_sistema.match(misionRegex);
    if (misionMatch && misionMatch[1]) {
      prompt_mision = misionMatch[1].trim();
    }

    // 2. Extraer ESPECIALIZACIÓN
    const especializacionRegex = /ESPECIALIZACIÓN:\s*\n([\s\S]*?)(?=\n\n(?:REGLAS|TONO)|$)/i;
    const especializacionMatch = prompt_sistema.match(especializacionRegex);
    if (especializacionMatch && especializacionMatch[1]) {
      prompt_especializado = especializacionMatch[1].trim();
    }

    // 3. Extraer REGLAS
    const reglasRegex = /REGLAS:\s*\n([\s\S]*?)(?=\n\nTONO:|$)/i;
    const reglasMatch = prompt_sistema.match(reglasRegex);
    if (reglasMatch && reglasMatch[1]) {
      const reglasText = reglasMatch[1].trim();
      prompt_reglas = reglasText
        .split('\n')
        .map(r => r.replace(/^-\s*/, '').trim())
        .filter(r => r.length > 0);
    }

    // Asegurar mínimo 2 reglas para el formulario
    if (prompt_reglas.length < 2) {
      while (prompt_reglas.length < 2) {
        prompt_reglas.push('');
      }
    }

    // 4. Extraer TONO
    const tonoRegex = /TONO:\s*\n([\s\S]*?)$/i;
    const tonoMatch = prompt_sistema.match(tonoRegex);
    if (tonoMatch && tonoMatch[1]) {
      const tonoText = tonoMatch[1].trim().toLowerCase();
      
      if (tonoText.includes('formal') && tonoText.includes('profesional')) {
        prompt_tono = 'formal';
      } else if (tonoText.includes('técnico') || tonoText.includes('tecnico')) {
        prompt_tono = 'tecnico';
      } else if (tonoText.includes('amigable') || tonoText.includes('cercano')) {
        prompt_tono = 'amigable';
      }
    }

  } catch (error) {
    console.error('❌ Error al parsear prompt_sistema:', error);
  }

  return {
    prompt_mision,
    prompt_reglas,
    prompt_tono,
    prompt_especializado,
  };
};

module.exports = {
  parsePromptSistema,
};