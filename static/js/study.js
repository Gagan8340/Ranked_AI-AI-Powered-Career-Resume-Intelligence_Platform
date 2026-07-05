const getAuthHeaders = () => ({});

const notify = (message, type = "info") => {
  if (window.showToast) {
    window.showToast(message, type);
  } else {
    alert(message);
  }
};

const uploadFileWithProgress = (file, onProgress) =>
  new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/study/upload");
    xhr.withCredentials = true;
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress((event.loaded / event.total) * 100);
      }
    };
    xhr.onload = () => {
      try {
        const data = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(data);
        } else {
          reject(new Error(data.message || "Upload failed"));
        }
      } catch (error) {
        reject(error);
      }
    };
    xhr.onerror = () => reject(new Error("Upload failed"));
    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });

const initStudyPlanner = () => {
  const uploadArea = document.getElementById("upload-area");
  const fileInput = document.getElementById("study-file");
  const browseBtn = document.getElementById("browse-btn");
  const preview = document.getElementById("upload-preview");
  const progressBar = document.getElementById("upload-progress");
  const extractBtn = document.getElementById("extract-btn");
  const uploadStatus = document.getElementById("upload-status");
  const uploadSteps = document.getElementById("upload-steps");
  const extractedTextEl = document.getElementById("extracted-text");
  const wordCountEl = document.getElementById("word-count");
  const summaryTextEl = document.getElementById("summary-text");
  const topicTagsEl = document.getElementById("topic-tags");
  const generatePlanBtn = document.getElementById("generate-plan-btn");
  const generateQuizBtn = document.getElementById("extract-generate-quiz-btn");
  const summarizeBtn = document.getElementById("summarize-btn");
  const examDateInput = document.getElementById("exam-date");
  const timeline = document.getElementById("plan-timeline");
  const progressLabel = document.getElementById("plan-progress-label");
  const planProgressBar = document.getElementById("plan-progress-bar");
  const progressRing = document.getElementById("plan-progress-circle");
  const progressPercent = document.getElementById("plan-progress-percent");
  const planHoursCompleted = document.getElementById("plan-hours-completed");
  const planHoursLeft = document.getElementById("plan-hours-left");
  const planInsight = document.getElementById("plan-insight");
  const weakTopicsList = document.getElementById("weak-topics-list");
  const chartCanvas = document.getElementById("performance-chart");



  let uploadedFile = null;
  let uploadedType = null;
  let extractedText = "";
  let planItems = [];
  let performanceChart = null;

  const steps = ["upload", "extract", "analyze", "build", "done"];

  const setStepState = (activeStep) => {
    if (!uploadSteps) return;
    const stepNodes = uploadSteps.querySelectorAll(".upload-step");
    stepNodes.forEach((node) => {
      const step = node.dataset.step;
      const stepIndex = steps.indexOf(step);
      const activeIndex = steps.indexOf(activeStep);
      node.classList.remove("is-active", "is-done");
      if (stepIndex < activeIndex) {
        node.classList.add("is-done");
      } else if (stepIndex === activeIndex) {
        node.classList.add("is-active");
      }
    });
  };

  const setUploadStatus = (text, step) => {
    if (uploadStatus) {
      uploadStatus.textContent = text;
    }
    if (step) {
      setStepState(step);
    }
  };

  const setRingProgress = (percent) => {
    if (!progressRing) return;
    const radius = 52;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percent / 100) * circumference;
    progressRing.style.strokeDasharray = `${circumference}`;
    progressRing.style.strokeDashoffset = `${offset}`;
    if (progressPercent) {
      progressPercent.textContent = `${percent}%`;
    }
  };

  const deriveSummary = (text) => {
    if (!text) return "Upload notes to generate a summary.";
    const sentences = text
      .replace(/\s+/g, " ")
      .split(/[.!?]\s+/)
      .filter((sentence) => sentence.length > 20)
      .slice(0, 3);
    return sentences.length ? `${sentences.join(". ")}.` : text.slice(0, 160);
  };

  const extractTags = (text) => {
    if (!text) return [];
    const words = text
      .toLowerCase()
      .replace(/[^a-z\s]/g, " ")
      .split(/\s+/)
      .filter((word) => word.length > 4);
    const counts = words.reduce((acc, word) => {
      acc[word] = (acc[word] || 0) + 1;
      return acc;
    }, {});
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([word]) => word);
  };

  const renderTags = (tags) => {
    if (!topicTagsEl) return;
    topicTagsEl.innerHTML = "";
    tags.forEach((tag) => {
      const chip = document.createElement("span");
      chip.className = "topic-tag";
      chip.textContent = tag;
      topicTagsEl.appendChild(chip);
    });
  };

  const renderPlan = () => {
    if (!timeline) return;
    timeline.innerHTML = "";
    const total = planItems.length;
    if (!total) {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      empty.textContent = "Your AI planner is ready when you are.";
      timeline.appendChild(empty);
      setRingProgress(0);
      if (planInsight) {
        planInsight.textContent = "Upload notes to build your personalized learning system.";
      }
      return;
    }
    const completed = planItems.filter((item) => item.is_completed).length;
    const percent = total ? Math.round((completed / total) * 100) : 0;
    progressLabel.textContent = `${percent}% complete`;
    if (planProgressBar) {
      planProgressBar.style.width = `${percent}%`;
    }
    setRingProgress(percent);

    const totalMinutes = planItems.reduce(
      (sum, item) => sum + (item.plan_data?.duration_minutes || 90),
      0
    );
    const completedMinutes = planItems.reduce(
      (sum, item) =>
        sum + (item.is_completed ? item.plan_data?.duration_minutes || 90 : 0),
      0
    );
    const remainingMinutes = Math.max(totalMinutes - completedMinutes, 0);
    if (planHoursCompleted) {
      planHoursCompleted.textContent = `${Math.round(completedMinutes / 60)}h`;
    }
    if (planHoursLeft) {
      planHoursLeft.textContent = `${Math.round(remainingMinutes / 60)}h`;
    }
    if (planInsight) {
      planInsight.textContent =
        percent >= 80
          ? "You are ahead of schedule by 2 days."
          : "Keep a steady pace to stay on track.";
    }

    planItems.forEach((plan) => {
      const card = document.createElement("div");
      card.className = `plan-card ${plan.is_completed ? "completed" : ""}`;
      const header = document.createElement("div");
      header.className = "plan-header";
      const title = document.createElement("div");
      title.innerHTML = `<strong>Day ${plan.plan_data?.day || ""}</strong> • ${plan.subject || ""}`;
      const date = document.createElement("span");
      date.className = "muted-text";
      date.textContent = plan.exam_date ? `Due ${plan.exam_date}` : "";
      header.appendChild(title);
      header.appendChild(date);

      const topic = document.createElement("div");
      topic.className = "muted-text";
      topic.textContent = plan.topic || plan.plan_data?.topic || "";

      const meta = document.createElement("div");
      meta.className = "plan-meta";

      const duration = document.createElement("span");
      duration.className = "badge";
      duration.textContent = `${plan.plan_data?.duration_minutes || 90} min`;
      const priority = document.createElement("span");
      const priorityValue = (plan.priority || "medium").toLowerCase();
      priority.className = `badge ${priorityValue}`;
      priority.textContent = priorityValue;

      meta.appendChild(duration);
      meta.appendChild(priority);

      const tasks = document.createElement("div");
      tasks.className = "plan-tasks";
      (plan.plan_data?.tasks || []).forEach((task) => {
        const taskRow = document.createElement("div");
        taskRow.className = `plan-task ${plan.is_completed ? "completed" : ""}`;
        taskRow.innerHTML = `<span>${plan.is_completed ? "✓" : "○"}</span><span>${task}</span>`;
        tasks.appendChild(taskRow);
      });

      const recommendation = document.createElement("div");
      recommendation.className = "plan-reco";
      recommendation.textContent = "AI recommendation: Focus on the highest priority concepts first.";

      const completeBtn = document.createElement("button");
      completeBtn.className = "btn-secondary";
      completeBtn.textContent = plan.is_completed ? "Completed" : "Mark Complete";
      completeBtn.disabled = plan.is_completed;
      completeBtn.addEventListener("click", async () => {
        card.classList.add("completing");
        const response = await window.apiFetch("/study/complete-task", {
          method: "POST",
          body: JSON.stringify({ plan_id: plan.id }),
        });
        if (response && response.ok) {
          plan.is_completed = true;
          renderPlan();
        }
      });

      card.appendChild(header);
      card.appendChild(topic);
      card.appendChild(meta);
      if (tasks.childElementCount) {
        card.appendChild(tasks);
      }
      card.appendChild(recommendation);
      card.appendChild(completeBtn);
      timeline.appendChild(card);
    });
  };

  const loadPlans = async () => {
    const response = await window.apiFetch("/study/plans");
    if (!response || !response.ok) return;
    const data = await response.json();
    planItems = data.plans || [];
    renderPlan();
  };

  const loadWeakTopics = async () => {
    const response = await window.apiFetch("/study/weak-topics");
    if (!response || !response.ok) return;
    const data = await response.json();
    weakTopicsList.innerHTML = "";
    (data.weak_topics || []).forEach((topic) => {
      const card = document.createElement("div");
      card.className = "weak-card weak";
      const text = document.createElement("div");
      text.textContent = topic;
      const btn = document.createElement("button");
      btn.className = "btn-secondary";
      btn.textContent = "Generate Quiz";
      btn.addEventListener("click", () => {
        window.location.href = `/quiz?topic=${encodeURIComponent(topic)}`;
      });
      card.appendChild(text);
      card.appendChild(btn);
      weakTopicsList.appendChild(card);
    });
  };

  const loadPerformance = async () => {
    if (!chartCanvas || !window.Chart) return;
    const response = await window.apiFetch("/study/subject-performance");
    if (!response || !response.ok) return;
    const data = await response.json();
    const labels = Object.keys(data.performance || {});
    const values = Object.values(data.performance || {});
    if (performanceChart) {
      performanceChart.destroy();
    }
    performanceChart = new Chart(chartCanvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Performance %",
            data: values,
            backgroundColor: values.map((value) =>
              value >= 70
                ? "rgba(16, 185, 129, 0.7)"
                : value >= 50
                ? "rgba(245, 158, 11, 0.7)"
                : "rgba(239, 68, 68, 0.7)"
            ),
            borderRadius: 8,
          },
        ],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { min: 0, max: 100, ticks: { color: "#94a3b8" } },
          y: { ticks: { color: "#94a3b8" } },
        },
      },
    });
  };

  const handleFile = async (file) => {
    if (!file) return;
    const validTypes = [
      "application/pdf",
      "image/png",
      "image/jpeg",
      "image/jpg",
    ];
    if (!validTypes.includes(file.type)) {
      notify("Only PDF, PNG, JPG files are allowed", "error");
      return;
    }
    preview.innerHTML = "";
    const card = document.createElement("div");
    card.className = "upload-file-card";
    card.innerHTML = `<span>${file.name}</span><span class="muted-text">${file.type}</span>`;
    preview.appendChild(card);
    progressBar.style.width = "0%";
    try {
      setUploadStatus("Uploading", "upload");
      const result = await uploadFileWithProgress(file, (percent) => {
        progressBar.style.width = `${percent}%`;
      });
      uploadedFile = result.file_path;
      uploadedType = result.file_type;
      extractBtn.disabled = false;
      generateQuizBtn.disabled = false;
      summarizeBtn.disabled = false;
      setUploadStatus("Upload complete", "done");
      notify("Upload complete", "success");
    } catch (error) {
      notify(error.message, "error");
    }
  };

  if (uploadArea) {
    uploadArea.addEventListener("dragover", (event) => {
      event.preventDefault();
      uploadArea.classList.add("drag-over");
    });
    uploadArea.addEventListener("dragleave", () => {
      uploadArea.classList.remove("drag-over");
    });
    uploadArea.addEventListener("drop", (event) => {
      event.preventDefault();
      uploadArea.classList.remove("drag-over");
      const file = event.dataTransfer.files[0];
      handleFile(file);
    });
  }
  if (browseBtn) browseBtn.addEventListener("click", () => fileInput.click());
  if (fileInput) fileInput.addEventListener("change", (event) => handleFile(event.target.files[0]));

  if (extractBtn) extractBtn.addEventListener("click", async () => {
    if (!uploadedFile || !uploadedType) return;
    extractBtn.disabled = true;
    uploadArea.classList.add("is-scanning");
    setUploadStatus("Extracting", "extract");
    const response = await window.apiFetch("/study/extract", {
      method: "POST",
      body: JSON.stringify({ file_path: uploadedFile, file_type: uploadedType }),
    });
    if (!response) {
      notify("Session expired. Please login again.", "error");
      extractBtn.disabled = false;
      uploadArea.classList.remove("is-scanning");
      return;
    }
    const data = await response.json();
    if (!response.ok) {
      notify(data.message || "Extraction failed", "error");
      extractBtn.disabled = false;
      uploadArea.classList.remove("is-scanning");
      return;
    }
    extractedText = data.extracted_text;
    extractedTextEl.textContent = extractedText || "No text detected.";
    wordCountEl.textContent = `${data.word_count || 0} words`;
    if (summaryTextEl) {
      summaryTextEl.textContent = deriveSummary(extractedText);
    }
    renderTags(extractTags(extractedText));
    setUploadStatus("Analyzing", "analyze");
    generatePlanBtn.disabled = false;
    extractBtn.disabled = false;
    setTimeout(() => setUploadStatus("Building", "build"), 800);
    setTimeout(() => {
      setUploadStatus("Ready", "done");
      uploadArea.classList.remove("is-scanning");
    }, 1600);
  });

  if (generatePlanBtn) generatePlanBtn.addEventListener("click", async () => {
    if (!extractedText) {
      notify("Extract text first", "error");
      return;
    }
    generatePlanBtn.disabled = true;
    const response = await window.apiFetch("/study/generate-plan", {
      method: "POST",
      body: JSON.stringify({
        extracted_text: extractedText,
        exam_date: examDateInput.value,
      }),
    });
    if (!response) {
      notify("Session expired. Please login again.", "error");
      generatePlanBtn.disabled = false;
      return;
    }
    const data = await response.json();
    if (!response.ok) {
      notify(data.message || "Plan generation failed", "error");
      generatePlanBtn.disabled = false;
      return;
    }
    notify("Study plan generated", "success");
    await loadPlans();
    await loadWeakTopics();
    await loadPerformance();
    generatePlanBtn.disabled = false;
  });

  if (generateQuizBtn) {
    generateQuizBtn.addEventListener("click", () => {
      if (!extractedText) {
        notify("Extract text first", "error");
        return;
      }
      const tags = extractTags(extractedText);
      const topic = tags.length ? tags[0] : "AI Generated Quiz";
      window.location.href = `/quiz?topic=${encodeURIComponent(topic)}`;
    });
  }

  if (summarizeBtn) {
    summarizeBtn.addEventListener("click", () => {
      if (!extractedText) {
        notify("Extract text first", "error");
        return;
      }
      if (summaryTextEl) {
        summaryTextEl.textContent = deriveSummary(extractedText);
      }
      notify("Summary updated", "success");
    });
  }

  setUploadStatus("Idle", "upload");
  loadPlans();
  loadWeakTopics();
  loadPerformance();
};

const initQuiz = () => {
  const setupPanel = document.getElementById("quiz-setup");
  const runnerPanel = document.getElementById("quiz-runner");
  const resultsPanel = document.getElementById("quiz-results");
  const generateBtn = document.getElementById("generate-quiz-btn");
  const loading = document.getElementById("quiz-loading");
  if (!setupPanel || !runnerPanel) {
    return;
  }

  const topicInput = document.getElementById("quiz-topic");
  const urlParams = new URLSearchParams(window.location.search);
  if (topicInput && urlParams.get("topic")) {
    topicInput.value = urlParams.get("topic");
  }

  let quizData = null;
  let currentIndex = 0;
  let answers = {};
  let correctAnswers = {};
  let timer = null;
  let timeLeft = 60;
  let quizStart = null;

  const questionCount = document.getElementById("question-count");
  const quizProgressBar = document.getElementById("quiz-progress-bar");
  const timerText = document.getElementById("timer-text");
  const timerRing = document.getElementById("timer-ring");
  const timerShell = document.getElementById("timer-shell");
  const questionEl = document.getElementById("quiz-question");
  const optionsEl = document.getElementById("quiz-options");
  const nextBtn = document.getElementById("next-question-btn");
  const dotsEl = document.getElementById("question-dots");
  const prevBtn = document.getElementById("prev-question-btn");

  const showPanel = (panel) => {
    setupPanel.style.display = panel === "setup" ? "block" : "none";
    runnerPanel.style.display = panel === "runner" ? "block" : "none";
    resultsPanel.style.display = panel === "results" ? "block" : "none";
  };

  const startTimer = () => {
    timeLeft = 60;
    timerText.textContent = `${timeLeft}s`;
    if (timerRing) {
      const circumference = 2 * Math.PI * 52;
      timerRing.style.strokeDasharray = `${circumference}`;
      timerRing.style.strokeDashoffset = "0";
      timerRing.style.stroke = "var(--green)";
    }
    if (timerShell) {
      timerShell.classList.remove("urgent");
    }
    clearInterval(timer);
    timer = setInterval(() => {
      timeLeft -= 1;
      timerText.textContent = `${timeLeft}s`;
      if (timerRing) {
        const circumference = 2 * Math.PI * 52;
        const offset = circumference - (timeLeft / 60) * circumference;
        timerRing.style.strokeDashoffset = `${offset}`;
      }
      if (timeLeft <= 10 && timerShell) {
        timerShell.classList.add("urgent");
      }
      if (timeLeft <= 0) {
        clearInterval(timer);
        nextQuestion();
      }
    }, 1000);
  };

  const renderDots = () => {
    dotsEl.innerHTML = "";
    quizData.questions.forEach((_, index) => {
      const dot = document.createElement("button");
      const answered = answers[String(quizData.questions[index].id)];
      dot.className = `dot ${index === currentIndex ? "active" : ""} ${
        answered ? "answered" : ""
      }`;
      dot.type = "button";
      dot.addEventListener("click", () => {
        currentIndex = index;
        renderQuestion();
      });
      dotsEl.appendChild(dot);
    });
  };

  const renderQuestion = () => {
    const question = quizData.questions[currentIndex];
    questionCount.textContent = `Question ${currentIndex + 1} of ${quizData.questions.length}`;
    quizProgressBar.style.width = `${((currentIndex + 1) / quizData.questions.length) * 100}%`;
    questionEl.textContent = question.question;
    optionsEl.innerHTML = "";
    Object.entries(question.options).forEach(([key, value]) => {
      const btn = document.createElement("button");
      btn.className = "option-card";
      btn.type = "button";
      btn.textContent = `${key}. ${value}`;
      if (answers[String(question.id)]) {
        btn.disabled = true;
        if (answers[String(question.id)] === key) {
          btn.classList.add("selected");
        }
      }
      btn.addEventListener("click", () => {
        if (answers[String(question.id)]) return;
        answers[String(question.id)] = key;
        btn.classList.add("selected");
        optionsEl.querySelectorAll("button").forEach((el) => (el.disabled = true));
        renderDots();
      });
      optionsEl.appendChild(btn);
    });
    renderDots();
    startTimer();
  };

  const submitQuiz = async () => {
    clearInterval(timer);
    const response = await window.apiFetch("/study/submit-quiz", {
      method: "POST",
      body: JSON.stringify({
        subject: quizData.subject,
        topic: quizData.topic,
        answers,
        correct_answers: correctAnswers,
        time_taken: Math.floor((Date.now() - quizStart) / 1000),
      }),
    });
    if (!response) {
      notify("Session expired. Please login again.", "error");
      return;
    }
    const data = await response.json();
    if (!response.ok) {
      notify(data.message || "Quiz submission failed", "error");
      return;
    }
    showResults(data);
  };

  const nextQuestion = () => {
    if (currentIndex < quizData.questions.length - 1) {
      currentIndex += 1;
      renderQuestion();
    } else {
      submitQuiz();
    }
  };

  const showResults = (result) => {
    showPanel("results");
    document.getElementById("score-display").textContent = `${result.score}/${result.total}`;
    document.getElementById("percentage-display").textContent = result.percentage;
    document.getElementById("time-display").textContent = result.time_taken || Math.floor((Date.now() - quizStart) / 1000);
    document.getElementById("correct-count").textContent = result.score;
    document.getElementById("wrong-count").textContent = result.total - result.score;
    const scoreMessage = document.getElementById("score-message");
    if (scoreMessage) {
      scoreMessage.textContent =
        result.percentage >= 80
          ? "Excellent progress"
          : result.percentage >= 60
          ? "Solid momentum"
          : "Let’s sharpen the basics";
    }
    const xpEarned = document.getElementById("xp-earned");
    if (xpEarned) {
      const xp = Math.max(40, result.score * 15);
      xpEarned.textContent = `+${xp} XP`;
    }
    const badge = document.getElementById("pass-badge");
    badge.textContent = result.passed ? "Passed" : "Needs Improvement";
    badge.className = `badge ${result.passed ? "low" : "high"}`;

    const ring = document.getElementById("results-ring");
    if (ring) {
      const circumference = 2 * Math.PI * 52;
      ring.style.strokeDasharray = `${circumference}`;
      ring.style.strokeDashoffset = `${circumference - (result.percentage / 100) * circumference}`;
    }

    const analysisSummary = document.getElementById("analysis-summary");
    const analysisList = document.getElementById("analysis-list");
    if (analysisSummary) {
      analysisSummary.textContent =
        result.percentage >= 80
          ? "You are strong on core concepts. Keep sharpening with harder drills."
          : result.percentage >= 60
          ? "Solid foundation. Focus on the weak areas to level up."
          : "Needs reinforcement. Revisit fundamentals and practice again.";
    }
    if (analysisList) {
      analysisList.innerHTML = "";
      const insights = [
        `Accuracy: ${result.percentage}%`,
        result.weak_topics?.length
          ? `Weak topics: ${result.weak_topics.join(", ")}`
          : "No weak topics detected.",
        "Recommended next focus: spaced practice and short review sessions.",
      ];
      insights.forEach((item) => {
        const row = document.createElement("div");
        row.textContent = item;
        analysisList.appendChild(row);
      });
    }

    const weakBox = document.getElementById("quiz-weak-topics");
    if (weakBox) {
      weakBox.innerHTML = result.weak_topics?.length
        ? `<strong>Weak Topics Detected:</strong> ${result.weak_topics.join(", ")}
           <div class="result-actions">
             <button class="btn-secondary" type="button" id="revision-plan-btn">Generate Revision Plan</button>
             <button class="btn-ghost" type="button" id="practice-again-btn">Practice Again</button>
             <button class="btn-primary" type="button" id="ask-ai-btn">Ask AI to Explain</button>
           </div>`
        : "No weak topics detected.";
    }

    const review = document.getElementById("quiz-review");
    review.innerHTML = "";
    quizData.questions.forEach((question) => {
      const item = document.createElement("div");
      const isCorrect = answers[String(question.id)] === question.correct_answer;
      item.className = `review-item ${isCorrect ? "correct" : "wrong"}`;
      item.innerHTML = `
        <strong>${question.question}</strong>
        <div>Your answer: ${answers[String(question.id)] || "Not answered"}</div>
        <div>Correct answer: ${question.correct_answer}</div>
        <div>${question.explanation}</div>
      `;
      review.appendChild(item);
    });

    const askAiBtn = document.getElementById("ask-ai-btn");
    if (askAiBtn) {
      askAiBtn.addEventListener("click", () => {
        const topic = result.weak_topics?.[0] || quizData.topic;
        localStorage.setItem("aiPrompt", `Explain ${topic} with examples`);
        window.location.href = "/chatbot";
      });
    }
    const revisionBtn = document.getElementById("revision-plan-btn");
    if (revisionBtn) {
      revisionBtn.addEventListener("click", () => {
        window.location.href = "/study";
      });
    }
    const practiceBtn = document.getElementById("practice-again-btn");
    if (practiceBtn) {
      practiceBtn.addEventListener("click", () => {
        showPanel("setup");
      });
    }
  };

  const generateQuiz = async () => {
    const subject = document.getElementById("quiz-subject").value;
    const topic = topicInput.value.trim();
    const difficulty = document.getElementById("quiz-difficulty").value;
    if (!subject) {
      notify("Select a subject", "error");
      return;
    }
    if (!topic) {
      notify("Enter a topic", "error");
      return;
    }
    loading.style.display = "block";
    generateBtn.disabled = true;
    const response = await window.apiFetch("/study/generate-quiz", {
      method: "POST",
      body: JSON.stringify({ subject, topic, difficulty }),
    });
    if (!response) {
      notify("Session expired. Please login again.", "error");
      return;
    }
    const data = await response.json();
    loading.style.display = "none";
    generateBtn.disabled = false;
    if (!response.ok) {
      notify(data.message || "Quiz generation failed", "error");
      return;
    }
    quizData = data;
    answers = {};
    correctAnswers = {};
    quizData.questions.forEach((q) => {
      correctAnswers[q.id] = q.correct_answer;
    });
    currentIndex = 0;
    quizStart = Date.now();
    showPanel("runner");
    renderQuestion();
  };

  generateBtn.addEventListener("click", generateQuiz);
  nextBtn.addEventListener("click", nextQuestion);
  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      if (currentIndex > 0) {
        currentIndex -= 1;
        renderQuestion();
      }
    });
  }
  document.getElementById("retake-btn").addEventListener("click", () => {
    showPanel("setup");
  });
  document.getElementById("study-weak-btn").addEventListener("click", () => {
    window.location.href = "/study";
  });

  document.addEventListener("keydown", (event) => {
    if (runnerPanel.style.display !== "block") return;
    if (event.key === "ArrowRight") {
      nextQuestion();
    }
    if (event.key === "ArrowLeft" && currentIndex > 0) {
      currentIndex -= 1;
      renderQuestion();
    }
    if (["1", "2", "3", "4"].includes(event.key)) {
      const buttons = optionsEl.querySelectorAll("button");
      const index = Number(event.key) - 1;
      if (buttons[index]) {
        buttons[index].click();
      }
    }
  });

  document.querySelectorAll(".pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".pill").forEach((btn) => btn.classList.remove("active"));
      pill.classList.add("active");
      document.getElementById("quiz-difficulty").value = pill.dataset.difficulty;
    });
  });
};

document.addEventListener("DOMContentLoaded", () => {
  initStudyPlanner();
  initQuiz();
});
