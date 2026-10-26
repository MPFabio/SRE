// Avis produits ShopEasy, étape 2 : métriques Prometheus.
package main

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type Review struct {
	Rating  int    `json:"rating"`
	Comment string `json:"comment"`
}

var (
	forbidden = []string{"arnaque", "nul"}

	mu      sync.Mutex
	reviews = map[int][]Review{}

	// Trafic et latence de chaque route.
	requests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "http_requests_total", Help: "Requêtes HTTP"}, []string{"method", "route", "status"})
	latency = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name: "http_request_duration_seconds", Help: "Durée des requêtes HTTP"}, []string{"method", "route"})

	// Métriques business.
	created = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "reviews_created_total", Help: "Avis publiés"}, []string{"rating"})
	rejected = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "reviews_rejected_total", Help: "Avis refusés"}, []string{"reason"})
	average = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "reviews_average_rating", Help: "Note moyenne par produit"}, []string{"product_id"})
)

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(body)
}

func isForbidden(comment string) bool {
	for _, word := range strings.Fields(strings.ToLower(comment)) {
		for _, f := range forbidden {
			if word == f {
				return true
			}
		}
	}
	return false
}

type recorder struct {
	http.ResponseWriter
	status int
}

func (r *recorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

// measure compte les requêtes d'une route et mesure leur durée.
func measure(route string, next http.HandlerFunc) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		start := time.Now()
		rec := &recorder{ResponseWriter: w, status: http.StatusOK}
		next(rec, req)
		requests.WithLabelValues(req.Method, route, strconv.Itoa(rec.status)).Inc()
		latency.WithLabelValues(req.Method, route).Observe(time.Since(start).Seconds())
	})
}

func listReviews(w http.ResponseWriter, req *http.Request) {
	id, err := strconv.Atoi(req.PathValue("product_id"))
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"detail": "product_id invalide"})
		return
	}
	mu.Lock()
	items := append([]Review{}, reviews[id]...)
	mu.Unlock()

	var avg any
	if len(items) > 0 {
		sum := 0
		for _, it := range items {
			sum += it.Rating
		}
		avg = float64(sum) / float64(len(items))
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"product_id": id, "count": len(items), "average": avg, "reviews": items})
}

func createReview(w http.ResponseWriter, req *http.Request) {
	id, err := strconv.Atoi(req.PathValue("product_id"))
	var review Review
	if err != nil || json.NewDecoder(req.Body).Decode(&review) != nil ||
		review.Rating < 1 || review.Rating > 5 || len(review.Comment) > 500 {
		rejected.WithLabelValues("validation").Inc()
		writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"detail": "avis invalide"})
		return
	}
	if isForbidden(review.Comment) {
		rejected.WithLabelValues("moderation").Inc()
		slog.Warn("avis refusé : modération", "product_id", id)
		writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"detail": "Avis refusé par la modération"})
		return
	}

	mu.Lock()
	reviews[id] = append(reviews[id], review)
	sum := 0
	for _, it := range reviews[id] {
		sum += it.Rating
	}
	average.WithLabelValues(strconv.Itoa(id)).Set(float64(sum) / float64(len(reviews[id])))
	mu.Unlock()

	created.WithLabelValues(strconv.Itoa(review.Rating)).Inc()
	slog.Info("avis publié", "product_id", id, "rating", review.Rating)
	writeJSON(w, http.StatusCreated, review)
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.Handle("GET /metrics", promhttp.Handler())
	mux.Handle("GET /api/reviews/{product_id}", measure("/api/reviews/{product_id}", listReviews))
	mux.Handle("POST /api/reviews/{product_id}", measure("/api/reviews/{product_id}", createReview))

	addr := ":" + env("PORT", "8086")
	slog.Info("démarrage", "addr", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		slog.Error("arrêt", "error", err)
		os.Exit(1)
	}
}
