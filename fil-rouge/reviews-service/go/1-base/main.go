// Avis produits ShopEasy, étape 1 : API et route de santé.
package main

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
)

type Review struct {
	Rating  int    `json:"rating"`
	Comment string `json:"comment"`
}

var (
	forbidden = []string{"arnaque", "nul"}

	mu      sync.Mutex
	reviews = map[int][]Review{}
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
		writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"detail": "avis invalide"})
		return
	}
	if isForbidden(review.Comment) {
		slog.Warn("avis refusé : modération", "product_id", id)
		writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"detail": "Avis refusé par la modération"})
		return
	}

	mu.Lock()
	reviews[id] = append(reviews[id], review)
	mu.Unlock()

	slog.Info("avis publié", "product_id", id, "rating", review.Rating)
	writeJSON(w, http.StatusCreated, review)
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /api/reviews/{product_id}", listReviews)
	mux.HandleFunc("POST /api/reviews/{product_id}", createReview)

	addr := ":" + env("PORT", "8086")
	slog.Info("démarrage", "addr", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		slog.Error("arrêt", "error", err)
		os.Exit(1)
	}
}
