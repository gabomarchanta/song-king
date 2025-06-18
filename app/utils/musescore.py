import os
import subprocess
import music21

def setup_musescore():
    """Configurar MuseScore para music21"""
    print("🔍 Buscando MuseScore...")
    
    # Verificar que nuestro launcher existe
    launcher_path = "/usr/local/bin/mscore-launcher"
    
    if os.path.exists(launcher_path):
        print(f"✅ MuseScore launcher encontrado: {launcher_path}")
        
        # Verificar que music21 ya está configurado
        try:
            us = music21.environment.UserSettings()
            try:
                current_path = str(us['musicxmlPath'])
            except:
                current_path = ''
            
            if current_path == launcher_path:
                print("✅ music21 ya está configurado correctamente")
            else:
                print("🔧 Reconfigurando music21...")
                us['musescoreDirectPNGPath'] = launcher_path
                us['musicxmlPath'] = launcher_path
                print("✅ music21 reconfigurado")
                
        except Exception as e:
            print(f"⚠️ Error configurando music21: {e}")
        
        return launcher_path
    else:
        print("❌ MuseScore launcher no encontrado. Ejecuta la configuración inicial.")
        return None

def generate_score_image(midi_file_path, output_path, format='svg'):
    """Generar imagen de partitura usando MuseScore"""
    try:
        print(f"📄 Generando partitura {format.upper()} desde: {midi_file_path}")
        
        # Cargar MIDI con music21
        score = music21.converter.parse(midi_file_path)
        
        # Mejorar configuración de la partitura
        score.insert(0, music21.metadata.Metadata())
        score.metadata.title = 'Transcripción Musical'
        score.metadata.composer = 'Song King AI'
        
        # Configurar instrumento apropiado
        for part in score.parts:
            if 'bass' in midi_file_path.lower():
                part.insert(0, music21.clef.BassClef())
            else:
                part.insert(0, music21.clef.TrebleClef())
                
        # Agregar compás si no existe
        if not score.getElementsByClass(music21.meter.TimeSignature):
            ts = music21.meter.TimeSignature('4/4')
            score.insert(0, ts)
            
        # Agregar tonalidad si no existe
        if not score.getElementsByClass(music21.key.KeySignature):
            ks = music21.key.KeySignature(0)  # C major
            score.insert(0, ks)
        
        # Guardar como MusicXML primero (siempre funciona)
        musicxml_path = output_path.replace('.svg', '.musicxml').replace('.png', '.musicxml')
        score.write('musicxml', fp=musicxml_path)
        print(f"✅ MusicXML guardado: {musicxml_path}")
        
        # Intentar generar imagen con music21 + MuseScore
        try:
            if format == 'svg':
                # Intentar SVG primero
                score.write('musicxml.png', fp=output_path)  # music21 debería usar MuseScore
                if os.path.exists(output_path):
                    print(f"✅ Partitura SVG generada: {output_path}")
                    return True
                else:
                    print(f"⚠️ SVG no se generó, intentando PNG...")
                    # Fallback a PNG
                    png_path = output_path.replace('.svg', '.png')
                    score.write('musicxml.png', fp=png_path)
                    if os.path.exists(png_path):
                        print(f"✅ Partitura PNG generada como fallback: {png_path}")
                        return True
            else:
                # Formato PNG
                score.write('musicxml.png', fp=output_path)
                if os.path.exists(output_path):
                    print(f"✅ Partitura PNG generada: {output_path}")
                    return True
                    
        except Exception as e:
            print(f"⚠️ Error generando {format} con music21: {e}")
            return False
                
    except Exception as e:
        print(f"❌ Error generando partitura: {e}")
        return False

def generate_all_score_formats(midi_file_path, base_output_path):
    """Generar todos los formatos de partitura disponibles"""
    base_name = os.path.splitext(base_output_path)[0]
    
    formats = {
        'musicxml': f"{base_name}.musicxml",
        'svg': f"{base_name}.svg", 
        'png': f"{base_name}.png"
    }
    
    generated = {}
    
    # Siempre intentar generar SVG primero, PNG como fallback
    svg_success = generate_score_image(midi_file_path, formats['svg'], 'svg')
    if svg_success and os.path.exists(formats['svg']):
        generated['svg'] = formats['svg']
    else:
        # Si SVG falla, intentar PNG
        png_success = generate_score_image(midi_file_path, formats['png'], 'png')
        if png_success and os.path.exists(formats['png']):
            generated['png'] = formats['png']
    
    # MusicXML siempre debería existir después de cualquier intento anterior
    if os.path.exists(formats['musicxml']):
        generated['musicxml'] = formats['musicxml']
    
    return generated 