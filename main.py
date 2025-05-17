from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import os
from datetime import datetime
from content_database import ContentDatabase
from models import db, Topic, Query

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "tu-clave-secreta-aqui"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Inicialización de la base de datos
db.init_app(app)

# Base de datos en memoria para compatibilidad
content_db = ContentDatabase()

@app.route('/')
def index():
    """Página principal con información sobre el bot y cómo usarlo."""
    topics = Topic.query.all()
    return render_template('index.html', topics=[topic.name for topic in topics])

@app.route('/topics')
def topics():
    """Devuelve la lista de temas disponibles en formato JSON."""
    topics = Topic.query.all()
    return jsonify([topic.name for topic in topics])

@app.route('/topic/<topic_name>')
def topic_detail(topic_name):
    """Devuelve la explicación de un tema específico."""
    topic = Topic.query.filter_by(name=topic_name.lower()).first()
    if topic:
        return jsonify({"topic": topic.name, "explanation": topic.explanation})
    else:
        return jsonify({"error": "Tema no encontrado"}), 404

@app.route('/search', methods=['POST'])
def search():
    """Busca un tema en el texto proporcionado."""
    if not request.json or 'text' not in request.json:
        return jsonify({"error": "Se requiere un texto para buscar"}), 400
    
    text = request.json['text'].lower()
    
    # Buscar temas en el texto
    found_topic = None
    all_topics = Topic.query.all()
    
    for topic in all_topics:
        if topic.name.lower() in text:
            found_topic = topic
            break
    
    # Registrar la consulta en la base de datos
    query = Query(
        user_name="Usuario Web",
        chat_id="web",
        query_text=text,
        matched_topic_id=found_topic.id if found_topic else None,
        successful=found_topic is not None
    )
    db.session.add(query)
    db.session.commit()
    
    if found_topic:
        return jsonify({"topic": found_topic.name, "explanation": found_topic.explanation})
    else:
        return jsonify({"error": "No se encontró ningún tema en el texto proporcionado"}), 404

# Rutas para la administración de temas
@app.route('/admin')
def admin():
    """Panel de administración para gestionar temas."""
    topics = Topic.query.all()
    return render_template('admin.html', topics=topics)

@app.route('/admin/topics/add', methods=['GET', 'POST'])
def add_topic():
    """Agregar un nuevo tema."""
    if request.method == 'POST':
        name = request.form.get('name')
        explanation = request.form.get('explanation')
        
        if not name or not explanation:
            flash('El nombre y la explicación son obligatorios', 'danger')
            return redirect(url_for('add_topic'))
        
        # Comprobar si el tema ya existe
        existing_topic = Topic.query.filter_by(name=name).first()
        if existing_topic:
            flash('Este tema ya existe', 'warning')
            return redirect(url_for('admin'))
        
        # Crear nuevo tema
        new_topic = Topic(name=name, explanation=explanation)
        db.session.add(new_topic)
        db.session.commit()
        
        flash('Tema agregado correctamente', 'success')
        return redirect(url_for('admin'))
    
    return render_template('add_topic.html')

@app.route('/admin/topics/edit/<int:id>', methods=['GET', 'POST'])
def edit_topic(id):
    """Editar un tema existente."""
    topic = Topic.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        explanation = request.form.get('explanation')
        
        if not name or not explanation:
            flash('El nombre y la explicación son obligatorios', 'danger')
            return redirect(url_for('edit_topic', id=id))
        
        # Comprobar si ya existe otro tema con el mismo nombre
        existing_topic = Topic.query.filter_by(name=name).first()
        if existing_topic and existing_topic.id != id:
            flash('Ya existe otro tema con este nombre', 'warning')
            return redirect(url_for('edit_topic', id=id))
        
        # Actualizar tema
        topic.name = name
        topic.explanation = explanation
        topic.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('Tema actualizado correctamente', 'success')
        return redirect(url_for('admin'))
    
    return render_template('edit_topic.html', topic=topic)

@app.route('/admin/topics/delete/<int:id>', methods=['POST'])
def delete_topic(id):
    """Eliminar un tema."""
    topic = Topic.query.get_or_404(id)
    db.session.delete(topic)
    db.session.commit()
    
    flash('Tema eliminado correctamente', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/queries')
def view_queries():
    """Ver todas las consultas realizadas por usuarios."""
    queries = Query.query.order_by(Query.timestamp.desc()).all()
    return render_template('queries.html', queries=queries)

# Crear todas las tablas de la base de datos
with app.app_context():
    db.create_all()
    
    # Importar datos iniciales de ContentDatabase a la base de datos
    # Solo si no hay temas en la base de datos
    if Topic.query.count() == 0:
        for topic_name, explanation in content_db.content.items():
            new_topic = Topic(name=topic_name, explanation=explanation)
            db.session.add(new_topic)
        db.session.commit()
        print("Datos iniciales importados a la base de datos.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)