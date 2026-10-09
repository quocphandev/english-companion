// Pure voice selection for read-aloud. Takes plain voice-like objects ({ lang, name }).

// BCP 47 tag set on each utterance, and preferred voice languages in order.
export const SPEECH_LANG = { en: "en-US", vi: "vi-VN" };
const PREFERRED_VOICE_LANGS = { en: ["en-US", "en-GB"], vi: ["vi-VN"] };

function normalizeLang(lang) {
  // Some platforms report "en_US" instead of "en-US".
  return (lang ?? "").replace("_", "-").toLowerCase();
}

/**
 * Pick the best voice for a language ("en" or "vi"), or null if none fits.
 * English prefers en-US, then en-GB, then any en-*; Vietnamese needs vi-*.
 */
export function pickVoice(voices, language) {
  for (const wanted of PREFERRED_VOICE_LANGS[language] ?? []) {
    const exact = voices.find((voice) => normalizeLang(voice.lang) === wanted.toLowerCase());
    if (exact) return exact;
  }
  return (
    voices.find((voice) => {
      const lang = normalizeLang(voice.lang);
      return lang === language || lang.startsWith(`${language}-`);
    }) ?? null
  );
}
