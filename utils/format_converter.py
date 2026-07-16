#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convertisseur de formats pour le Transcripteur Audio Pro
Support multiple des formats de sortie
Créé par Négus Dja
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class FormatConverter:
    """Convertisseur pour différents formats de transcription"""
    
    def __init__(self):
        self.supported_formats = {
            "text": "Texte simple",
            "srt": "Sous-titres SubRip",
            "vtt": "WebVTT",
            "json": "JSON structuré",
            "docx": "Document Word (HTML)",
            "csv": "Tableur CSV"
        }
    
    def convert(self, text: str, segments: List[Dict[str, Any]], 
                output_format: str, **options) -> str:
        """
        Convertit une transcription vers le format demandé
        
        Args:
            text: Texte de la transcription
            segments: Segments avec timestamps
            output_format: Format de sortie
            **options: Options spécifiques au format
            
        Returns:
            Contenu formaté
        """
        try:
            if output_format == "text":
                return self.to_text(text, **options)
            elif output_format == "srt":
                return self.to_srt(segments, **options)
            elif output_format == "vtt":
                return self.to_vtt(segments, **options)
            elif output_format == "json":
                return self.to_json(text, segments, **options)
            elif output_format == "docx":
                return self.to_docx_content(text, segments, **options)
            elif output_format == "csv":
                return self.to_csv(segments, **options)
            else:
                raise ValueError(f"Format non supporté: {output_format}")
                
        except Exception as e:
            logger.error(f"Erreur conversion vers {output_format}: {e}")
            raise
    
    def to_text(self, text: str, **options) -> str:
        """
        Convertit en texte simple avec options de formatage
        
        Args:
            text: Texte source
            **options: Options (paragraph_break, line_length, etc.)
            
        Returns:
            Texte formaté
        """
        formatted_text = text.strip()
        
        # Options de formatage
        paragraph_break = options.get("paragraph_break", True)
        line_length = options.get("line_length", 80)
        add_timestamps = options.get("add_timestamps", False)
        
        if paragraph_break:
            # Ajouter des retours à la ligne après certains signes de ponctuation
            formatted_text = re.sub(r'([.!?])\s+', r'\1\n\n', formatted_text)
        
        if line_length and line_length > 0:
            # Découper les lignes trop longues
            formatted_text = self._wrap_text(formatted_text, line_length)
        
        # Ajouter un en-tête si demandé
        if options.get("add_header", False):
            header = f"Transcription générée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n"
            header += f"Générée par Transcripteur Audio Pro - Négus Dja\n"
            header += "=" * 50 + "\n\n"
            formatted_text = header + formatted_text
        
        # Ajouter un pied de page
        if options.get("add_footer", False):
            footer = f"\n\n" + "=" * 50
            footer += f"\nTranscription terminée - {len(text.split())} mots"
            formatted_text += footer
        
        return formatted_text
    
    def to_srt(self, segments: List[Dict[str, Any]], **options) -> str:
        """
        Convertit en format SubRip (.srt)
        
        Args:
            segments: Segments avec timestamps
            **options: Options de formatage
            
        Returns:
            Contenu SRT
        """
        if not segments:
            # Créer des segments artificiels si pas de timing
            segments = self._create_artificial_segments(
                options.get("text", ""), 
                options.get("segment_duration", 3.0)
            )
        
        srt_content = []
        max_chars_per_line = options.get("max_chars_per_line", 42)
        max_lines = options.get("max_lines", 2)
        
        for i, segment in enumerate(segments, 1):
            if not segment.get("text", "").strip():
                continue
                
            start_time = self._format_srt_time(segment.get("start", 0))
            end_time = self._format_srt_time(segment.get("end", 0))
            text = segment["text"].strip()
            
            # Diviser le texte en lignes si nécessaire
            lines = self._split_text_for_subtitles(text, max_chars_per_line, max_lines)
            
            srt_content.append(str(i))
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.extend(lines)
            srt_content.append("")  # Ligne vide entre les segments
        
        return "\n".join(srt_content)
    
    def to_vtt(self, segments: List[Dict[str, Any]], **options) -> str:
        """
        Convertit en format WebVTT (.vtt)
        
        Args:
            segments: Segments avec timestamps
            **options: Options de formatage
            
        Returns:
            Contenu VTT
        """
        if not segments:
            segments = self._create_artificial_segments(
                options.get("text", ""), 
                options.get("segment_duration", 3.0)
            )
        
        vtt_content = ["WEBVTT"]
        
        # Ajouter des métadonnées si demandé
        if options.get("add_metadata", True):
            vtt_content.append("")
            vtt_content.append("NOTE")
            vtt_content.append(f"Généré par Transcripteur Audio Pro - Négus Dja")
            vtt_content.append(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        vtt_content.append("")
        
        max_chars_per_line = options.get("max_chars_per_line", 42)
        max_lines = options.get("max_lines", 2)
        
        for segment in segments:
            if not segment.get("text", "").strip():
                continue
                
            start_time = self._format_vtt_time(segment.get("start", 0))
            end_time = self._format_vtt_time(segment.get("end", 0))
            text = segment["text"].strip()
            
            # Diviser le texte en lignes
            lines = self._split_text_for_subtitles(text, max_chars_per_line, max_lines)
            
            vtt_content.append(f"{start_time} --> {end_time}")
            vtt_content.extend(lines)
            vtt_content.append("")
        
        return "\n".join(vtt_content)
    
    def to_json(self, text: str, segments: List[Dict[str, Any]], **options) -> str:
        """
        Convertit en format JSON structuré
        
        Args:
            text: Texte complet
            segments: Segments avec timestamps
            **options: Options d'export
            
        Returns:
            JSON formaté
        """
        # Calcul de statistiques
        words = text.split() if text else []
        word_count = len(words)
        char_count = len(text) if text else 0
        
        total_duration = 0
        if segments:
            total_duration = max(seg.get("end", 0) for seg in segments)
        
        # Structure JSON complète
        json_data = {
            "metadata": {
                "generator": "Transcripteur Audio Pro",
                "author": "Négus Dja",
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0",
                "language": options.get("language", "auto"),
                "model_used": options.get("model_used", "unknown"),
                "engine": options.get("engine", "unknown")
            },
            "statistics": {
                "total_duration": round(total_duration, 2),
                "word_count": word_count,
                "character_count": char_count,
                "segment_count": len(segments),
                "words_per_minute": round(word_count / (total_duration / 60), 1) if total_duration > 0 else 0,
                "average_confidence": self._calculate_average_confidence(segments)
            },
            "content": {
                "full_text": text,
                "segments": segments
            }
        }
        
        # Ajouter les informations de locuteurs si disponibles
        if any("speaker" in seg for seg in segments):
            speakers = list(set(seg.get("speaker", "UNKNOWN") for seg in segments))
            json_data["speakers"] = {
                "count": len(speakers),
                "list": speakers,
                "segments_by_speaker": self._group_segments_by_speaker(segments)
            }
        
        # Options de formatage JSON
        indent = options.get("indent", 2)
        ensure_ascii = options.get("ensure_ascii", False)
        
        return json.dumps(json_data, indent=indent, ensure_ascii=ensure_ascii, 
                         default=str, sort_keys=True)
    
    def to_csv(self, segments: List[Dict[str, Any]], **options) -> str:
        """
        Convertit en format CSV pour analyse
        
        Args:
            segments: Segments avec timestamps
            **options: Options d'export
            
        Returns:
            Contenu CSV
        """
        import csv
        import io
        
        output = io.StringIO()
        
        # Déterminer les colonnes selon les données disponibles
        columns = ["segment_id", "start_time", "end_time", "duration", "text", "word_count"]
        
        if segments and "confidence" in segments[0]:
            columns.append("confidence")
        if segments and "speaker" in segments[0]:
            columns.append("speaker")
        if segments and "words" in segments[0]:
            columns.append("word_level_data")
        
        writer = csv.DictWriter(output, fieldnames=columns, delimiter=options.get("delimiter", ","))
        
        # En-tête
        writer.writeheader()
        
        # Données
        for i, segment in enumerate(segments, 1):
            row = {
                "segment_id": i,
                "start_time": segment.get("start", 0),
                "end_time": segment.get("end", 0),
                "duration": round(segment.get("end", 0) - segment.get("start", 0), 2),
                "text": segment.get("text", "").replace('"', '""'),  # Échapper les guillemets
                "word_count": len(segment.get("text", "").split())
            }
            
            if "confidence" in columns:
                row["confidence"] = segment.get("confidence", 0)
            if "speaker" in columns:
                row["speaker"] = segment.get("speaker", "UNKNOWN")
            if "word_level_data" in columns:
                row["word_level_data"] = len(segment.get("words", []))
            
            writer.writerow(row)
        
        return output.getvalue()
    
    def to_docx_content(self, text: str, segments: List[Dict[str, Any]], **options) -> str:
        """
        Génère le contenu pour un document Word (format HTML simple)
        
        Args:
            text: Texte complet
            segments: Segments avec timestamps
            **options: Options de formatage
            
        Returns:
            Contenu HTML pour Word
        """
        html_content = []
        
        # En-tête du document
        html_content.append("<html><head><meta charset='utf-8'></head><body>")
        html_content.append(f"<h1>Transcription Audio</h1>")
        html_content.append(f"<p><em>Générée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</em></p>")
        html_content.append(f"<p><em>Créée avec Transcripteur Audio Pro - Négus Dja</em></p>")
        html_content.append("<hr>")
        
        # Statistiques
        if segments:
            total_duration = max(seg.get("end", 0) for seg in segments)
            word_count = len(text.split()) if text else 0
            
            html_content.append("<h2>Statistiques</h2>")
            html_content.append("<ul>")
            html_content.append(f"<li>Durée: {self._format_duration(total_duration)}</li>")
            html_content.append(f"<li>Nombre de mots: {word_count}</li>")
            html_content.append(f"<li>Nombre de segments: {len(segments)}</li>")
            html_content.append("</ul>")
        
        # Contenu selon le format demandé
        format_style = options.get("format_style", "paragraphs")
        
        if format_style == "segments" and segments:
            html_content.append("<h2>Transcription avec timestamps</h2>")
            for segment in segments:
                start = self._format_duration(segment.get("start", 0))
                end = self._format_duration(segment.get("end", 0))
                text_seg = segment.get("text", "").strip()
                
                if text_seg:
                    html_content.append(f"<p><strong>[{start} - {end}]</strong> {text_seg}</p>")
        else:
            # Format paragraphes
            html_content.append("<h2>Transcription</h2>")
            paragraphs = text.split('\n\n') if '\n\n' in text else [text]
            
            for para in paragraphs:
                if para.strip():
                    html_content.append(f"<p>{para.strip()}</p>")
        
        html_content.append("</body></html>")
        
        return "\n".join(html_content)
    
    def _create_artificial_segments(self, text: str, segment_duration: float = 3.0) -> List[Dict[str, Any]]:
        """Crée des segments artificiels quand les timestamps ne sont pas disponibles"""
        if not text:
            return []
        
        # Diviser par phrases
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        segments = []
        current_time = 0.0
        
        for sentence in sentences:
            if sentence:
                # Estimer la durée basée sur le nombre de mots
                words = len(sentence.split())
                estimated_duration = max(segment_duration, words * 0.4)  # 0.4s par mot
                
                segments.append({
                    "start": current_time,
                    "end": current_time + estimated_duration,
                    "text": sentence + ".",
                    "confidence": 0.8  # Estimation
                })
                
                current_time += estimated_duration
        
        return segments
    
    def _format_srt_time(self, seconds: float) -> str:
        """Formate le temps pour SRT (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _format_vtt_time(self, seconds: float) -> str:
        """Formate le temps pour VTT (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    
    def _format_duration(self, seconds: float) -> str:
        """Formate une durée de façon lisible"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h{minutes:02d}m{secs:02d}s"
        elif minutes > 0:
            return f"{minutes}m{secs:02d}s"
        else:
            return f"{secs}s"
    
    def _split_text_for_subtitles(self, text: str, max_chars: int, max_lines: int) -> List[str]:
        """Divise le texte en lignes adaptées aux sous-titres"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            # Vérifier si ajouter ce mot dépasserait la limite
            test_line = current_line + (" " if current_line else "") + word
            
            if len(test_line) <= max_chars:
                current_line = test_line
            else:
                # Ajouter la ligne actuelle et commencer une nouvelle
                if current_line:
                    lines.append(current_line)
                current_line = word
                
                # Limiter le nombre de lignes
                if len(lines) >= max_lines:
                    # Ajouter les mots restants à la dernière ligne
                    remaining_words = words[words.index(word):]
                    if remaining_words:
                        lines[-1] += " " + " ".join(remaining_words)
                    break
        
        # Ajouter la dernière ligne
        if current_line and len(lines) < max_lines:
            lines.append(current_line)
        
        return lines
    
    def _wrap_text(self, text: str, line_length: int) -> str:
        """Découpe le texte en lignes de longueur maximale"""
        import textwrap
        
        paragraphs = text.split('\n\n')
        wrapped_paragraphs = []
        
        for paragraph in paragraphs:
            if paragraph.strip():
                wrapped = textwrap.fill(paragraph, width=line_length)
                wrapped_paragraphs.append(wrapped)
            else:
                wrapped_paragraphs.append("")
        
        return '\n\n'.join(wrapped_paragraphs)
    
    def _calculate_average_confidence(self, segments: List[Dict[str, Any]]) -> float:
        """Calcule la confiance moyenne des segments"""
        if not segments:
            return 0.0
        
        confidences = [seg.get("confidence", 0.0) for seg in segments if "confidence" in seg]
        
        if not confidences:
            return 0.0
        
        return round(sum(confidences) / len(confidences), 3)
    
    def _group_segments_by_speaker(self, segments: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Groupe les segments par locuteur"""
        speakers_segments = {}
        
        for segment in segments:
            speaker = segment.get("speaker", "UNKNOWN")
            if speaker not in speakers_segments:
                speakers_segments[speaker] = []
            speakers_segments[speaker].append(segment)
        
        return speakers_segments
    
    def export_with_formatting(self, text: str, segments: List[Dict[str, Any]], 
                              output_format: str, style_options: Dict[str, Any]) -> str:
        """
        Export avec options de style avancées
        
        Args:
            text: Texte source
            segments: Segments avec timestamps
            output_format: Format de sortie
            style_options: Options de style spécifiques
            
        Returns:
            Contenu formaté avec style
        """
        try:
            if output_format == "srt":
                return self._export_styled_srt(segments, style_options)
            elif output_format == "vtt":
                return self._export_styled_vtt(segments, style_options)
            elif output_format == "html":
                return self._export_styled_html(text, segments, style_options)
            else:
                # Format standard
                return self.convert(text, segments, output_format, **style_options)
                
        except Exception as e:
            logger.error(f"Erreur export avec style: {e}")
            raise
    
    def _export_styled_srt(self, segments: List[Dict[str, Any]], style_options: Dict[str, Any]) -> str:
        """Export SRT avec styles (couleurs par locuteur, etc.)"""
        srt_content = []
        speaker_colors = style_options.get("speaker_colors", {})
        
        for i, segment in enumerate(segments, 1):
            if not segment.get("text", "").strip():
                continue
            
            start_time = self._format_srt_time(segment.get("start", 0))
            end_time = self._format_srt_time(segment.get("end", 0))
            text = segment["text"].strip()
            
            # Ajouter la couleur par locuteur
            speaker = segment.get("speaker")
            if speaker and speaker in speaker_colors:
                text = f'<font color="{speaker_colors[speaker]}">{text}</font>'
            
            # Ajouter le nom du locuteur si demandé
            if style_options.get("show_speaker_names", False) and speaker:
                text = f"<b>{speaker}:</b> {text}"
            
            srt_content.append(str(i))
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(text)
            srt_content.append("")
        
        return "\n".join(srt_content)
    
    def _export_styled_vtt(self, segments: List[Dict[str, Any]], style_options: Dict[str, Any]) -> str:
        """Export VTT avec styles CSS"""
        vtt_content = ["WEBVTT"]
        
        # Ajouter les styles CSS si demandé
        if style_options.get("add_css_styles", False):
            vtt_content.append("")
            vtt_content.append("STYLE")
            vtt_content.append("::cue(.speaker1) { color: #ff6b6b; }")
            vtt_content.append("::cue(.speaker2) { color: #4ecdc4; }")
            vtt_content.append("::cue(.speaker3) { color: #45b7d1; }")
            vtt_content.append("::cue(.high-confidence) { font-weight: bold; }")
            vtt_content.append("::cue(.low-confidence) { font-style: italic; opacity: 0.8; }")
        
        vtt_content.append("")
        
        for segment in segments:
            if not segment.get("text", "").strip():
                continue
            
            start_time = self._format_vtt_time(segment.get("start", 0))
            end_time = self._format_vtt_time(segment.get("end", 0))
            text = segment["text"].strip()
            
            # Appliquer les classes CSS selon les données
            css_classes = []
            
            speaker = segment.get("speaker")
            if speaker:
                speaker_class = f"speaker{hash(speaker) % 3 + 1}"  # Distribuer les locuteurs
                css_classes.append(speaker_class)
            
            confidence = segment.get("confidence", 0.5)
            if confidence > 0.8:
                css_classes.append("high-confidence")
            elif confidence < 0.3:
                css_classes.append("low-confidence")
            
            # Ligne de timing avec classes
            timing_line = f"{start_time} --> {end_time}"
            if css_classes:
                timing_line += f" line:1 position:50% align:center class:{' '.join(css_classes)}"
            
            vtt_content.append(timing_line)
            
            # Ajouter le nom du locuteur si demandé
            if style_options.get("show_speaker_names", False) and speaker:
                text = f"<v {speaker}>{text}</v>"
            
            vtt_content.append(text)
            vtt_content.append("")
        
        return "\n".join(vtt_content)
    
    def _export_styled_html(self, text: str, segments: List[Dict[str, Any]], 
                           style_options: Dict[str, Any]) -> str:
        """Export HTML avec mise en forme complète"""
        html_content = []
        
        # En-tête HTML avec CSS
        html_content.append("""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcription Audio Pro</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #4ecdc4;
            padding-bottom: 20px;
        }
        .stats {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .segment {
            margin-bottom: 15px;
            padding: 10px;
            border-left: 3px solid #4ecdc4;
            background: #fafafa;
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
            font-weight: bold;
        }
        .speaker {
            color: #ff6b6b;
            font-weight: bold;
        }
        .confidence-high { opacity: 1; }
        .confidence-medium { opacity: 0.8; }
        .confidence-low { opacity: 0.6; font-style: italic; }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">""")
        
        # En-tête
        html_content.append(f"""
        <div class="header">
            <h1>🎙️ Transcription Audio</h1>
            <p>Générée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
            <p><em>Transcripteur Audio Pro - Négus Dja</em></p>
        </div>""")
        
        # Statistiques
        if segments:
            total_duration = max(seg.get("end", 0) for seg in segments)
            word_count = len(text.split()) if text else 0
            avg_confidence = self._calculate_average_confidence(segments)
            
            html_content.append(f"""
        <div class="stats">
            <h3>📊 Statistiques</h3>
            <p><strong>Durée:</strong> {self._format_duration(total_duration)}</p>
            <p><strong>Mots:</strong> {word_count}</p>
            <p><strong>Segments:</strong> {len(segments)}</p>
            <p><strong>Confiance moyenne:</strong> {avg_confidence:.1%}</p>
        </div>""")
        
        # Contenu selon le style
        display_style = style_options.get("display_style", "segments")
        
        if display_style == "segments" and segments:
            html_content.append('<div class="segments"><h3>📝 Transcription détaillée</h3>')
            
            for segment in segments:
                start = self._format_duration(segment.get("start", 0))
                end = self._format_duration(segment.get("end", 0))
                text_seg = segment.get("text", "").strip()
                confidence = segment.get("confidence", 0.5)
                speaker = segment.get("speaker")
                
                # Classe CSS selon la confiance
                conf_class = "confidence-high" if confidence > 0.7 else \
                            "confidence-medium" if confidence > 0.4 else "confidence-low"
                
                if text_seg:
                    speaker_info = f'<span class="speaker">{speaker}:</span> ' if speaker else ""
                    
                    html_content.append(f"""
                <div class="segment {conf_class}">
                    <div class="timestamp">[{start} - {end}]</div>
                    <div class="text">{speaker_info}{text_seg}</div>
                </div>""")
            
            html_content.append('</div>')
        else:
            # Affichage en texte continu
            html_content.append('<div class="continuous-text">')
            html_content.append('<h3>📝 Transcription</h3>')
            
            paragraphs = text.split('\n\n') if '\n\n' in text else [text]
            for para in paragraphs:
                if para.strip():
                    html_content.append(f'<p>{para.strip()}</p>')
            
            html_content.append('</div>')
        
        # Pied de page
        html_content.append(f"""
        <div class="footer">
            <p>🎯 Créé avec Transcripteur Audio Pro</p>
            <p>👨‍🎨 Développé par Négus Dja - Directeur Artistique Guadeloupe</p>
            <p>🔧 Optimisé pour les ingénieurs son et vidéastes</p>
        </div>
    </div>
</body>
</html>""")
        
        return "\n".join(html_content)
    
    def get_supported_formats(self) -> Dict[str, str]:
        """Retourne la liste des formats supportés"""
        return self.supported_formats.copy()
    
    def validate_format_options(self, output_format: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valide et normalise les options pour un format donné
        
        Args:
            output_format: Format de sortie
            options: Options à valider
            
        Returns:
            Options validées et normalisées
        """
        validated_options = options.copy()
        
        if output_format == "srt":
            validated_options.setdefault("max_chars_per_line", 42)
            validated_options.setdefault("max_lines", 2)
            
        elif output_format == "vtt":
            validated_options.setdefault("max_chars_per_line", 42)
            validated_options.setdefault("max_lines", 2)
            validated_options.setdefault("add_metadata", True)
            
        elif output_format == "text":
            validated_options.setdefault("line_length", 80)
            validated_options.setdefault("paragraph_break", True)
            
        elif output_format == "json":
            validated_options.setdefault("indent", 2)
            validated_options.setdefault("ensure_ascii", False)
            
        elif output_format == "csv":
            validated_options.setdefault("delimiter", ",")
        
        return validated_options