from collections import defaultdict


def analyze_weak_topics(student_id, db_connection):
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT topic, AVG((score / total_questions) * 100) AS avg_score
            FROM quiz_results
            WHERE student_id=%s AND total_questions > 0
            GROUP BY topic
            """,
            (student_id,),
        )
        rows = cursor.fetchall()

    weak = []
    critical = []
    strong = []
    for row in rows:
        avg_score = float(row["avg_score"] or 0)
        if avg_score < 40:
            critical.append(row["topic"])
        elif avg_score < 60:
            weak.append(row["topic"])
        else:
            strong.append(row["topic"])

    recommended_focus = critical + [topic for topic in weak if topic not in critical]
    return {
        "weak": weak,
        "critical": critical,
        "strong": strong,
        "recommended_focus": recommended_focus[:5],
    }


def predict_struggle_topics(student_id, db_connection):
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT topic, score, total_questions, created_at
            FROM quiz_results
            WHERE student_id=%s
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (student_id,),
        )
        rows = cursor.fetchall()

    failures = defaultdict(int)
    topic_scores = defaultdict(list)
    for row in rows:
        percentage = (row["score"] / row["total_questions"]) * 100 if row["total_questions"] else 0
        topic_scores[row["topic"]].append(percentage)
        if percentage < 60:
            failures[row["topic"]] += 1

    predicted = set()
    for topic, count in failures.items():
        if count > 2:
            predicted.add(topic)

    for topic, scores in topic_scores.items():
        if len(scores) >= 3 and scores[0] < scores[-1]:
            predicted.add(topic)

    return list(predicted)


def get_subject_performance(student_id, db_connection):
    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT subject, AVG((score / total_questions) * 100) AS avg_score
            FROM quiz_results
            WHERE student_id=%s AND total_questions > 0
            GROUP BY subject
            """,
            (student_id,),
        )
        rows = cursor.fetchall()

    performance = {}
    for row in rows:
        performance[row["subject"]] = float(row["avg_score"] or 0)
    return performance


def generate_recommendations(student_id, db_connection):
    weak_data = analyze_weak_topics(student_id, db_connection)
    struggle_topics = predict_struggle_topics(student_id, db_connection)
    combined = weak_data["critical"] + weak_data["weak"] + struggle_topics
    seen = set()
    recommendations = []
    for topic in combined:
        if topic not in seen:
            recommendations.append(topic)
            seen.add(topic)
        if len(recommendations) >= 5:
            break
    return recommendations
