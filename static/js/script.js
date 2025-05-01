function showResults(electionId) {
  document.getElementById("resultsContent").innerHTML =
    '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';

  fetch(`/api/election/${electionId}/results`)
    .then((response) => {
      if (!response.ok) {
        if (response.status === 403) {
          throw new Error(
            "Results are only available after the election has ended"
          );
        }
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      console.log("Results data:", data);

      let resultsHtml = `
                <h3>${data.title}</h3>
                <p>${data.description}</p>
                <p><strong>Status:</strong> <span class="badge bg-${
                  data.status === "active" ? "success" : "secondary"
                }">${data.status}</span></p>
                
                <div class="mt-4">
                    <h4>Vote Counts</h4>
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Candidate</th>
                                    <th>Party</th>
                                    <th>Votes</th>
                                </tr>
                            </thead>
                            <tbody>`;

      data.candidates.forEach((candidate) => {
        const voteCount = data.votes[candidate.id] || 0;
        resultsHtml += `
                    <tr>
                        <td>${candidate.name}</td>
                        <td>${candidate.party}</td>
                        <td>${voteCount}</td>
                    </tr>`;
      });

      resultsHtml += `
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="mt-4" style="height: 300px; width: 100%;">
                    <canvas id="resultsChart"></canvas>
                </div>`;

      document.getElementById("resultsContent").innerHTML = resultsHtml;

      // Check if Chart is defined before using it
      if (typeof Chart !== "undefined") {
        setTimeout(() => {
          const ctx = document.getElementById("resultsChart");
          if (!ctx) {
            console.error("Chart canvas element not found");
            return;
          }

          console.log("Creating chart with data:", {
            labels: data.candidates.map((c) => c.name),
            data: data.candidates.map((c) => data.votes[c.id] || 0),
          });

          try {
            new Chart(ctx, {
              type: "bar",
              data: {
                labels: data.candidates.map((c) => c.name),
                datasets: [
                  {
                    label: "Votes",
                    data: data.candidates.map((c) => data.votes[c.id] || 0),
                    backgroundColor: [
                      "rgba(0, 179, 159, 0.7)",
                      "rgba(0, 94, 184, 0.7)",
                      "rgba(0, 199, 226, 0.7)",
                      "rgba(255, 99, 132, 0.7)",
                      "rgba(255, 206, 86, 0.7)",
                      "rgba(153, 102, 255, 0.7)",
                    ],
                    borderColor: [
                      "rgba(0, 179, 159, 1)",
                      "rgba(0, 94, 184, 1)",
                      "rgba(0, 199, 226, 1)",
                      "rgba(255, 99, 132, 1)",
                      "rgba(255, 206, 86, 1)",
                      "rgba(153, 102, 255, 1)",
                    ],
                    borderWidth: 1,
                  },
                ],
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                  yAxes: [
                    {
                      ticks: {
                        beginAtZero: true,
                        min: 0,
                        stepSize: 1,
                        precision: 0,
                        fontColor: "white",
                      },
                      gridLines: {
                        color: "rgba(255, 255, 255, 0.1)",
                      },
                    },
                  ],
                  xAxes: [
                    {
                      ticks: {
                        fontColor: "white",
                      },
                      gridLines: {
                        color: "rgba(255, 255, 255, 0.1)",
                      },
                    },
                  ],
                },
                legend: {
                  display: false,
                },
                tooltips: {
                  backgroundColor: "rgba(0, 0, 0, 0.8)",
                  titleFontColor: "white",
                  bodyFontColor: "white",
                  displayColors: false,
                },
                animation: {
                  duration: 1000,
                },
                barPercentage: 0.6,
                categoryPercentage: 0.7,
                layout: {
                  padding: 20,
                },
              },
            });
            console.log("Chart created successfully");
          } catch (error) {
            console.error("Error creating chart:", error);
          }
        }, 100); // Small delay to ensure DOM is ready
      } else {
        console.warn("Chart.js is not loaded. Cannot display chart.");
        document
          .getElementById("resultsChart")
          .insertAdjacentHTML(
            "afterend",
            '<div class="alert alert-warning mt-2">Chart visualization is not available. Chart.js library could not be loaded.</div>'
          );
      }
    })
    .catch((error) => {
      console.error("Error fetching results:", error);
      document.getElementById("resultsContent").innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle"></i> 
                    ${
                      error.message ||
                      "Error loading results. Please try again later."
                    }
                </div>`;
    });
}

function confirmDeleteElection(electionId, electionTitle) {
  document.getElementById(
    "deleteElectionModalBody"
  ).innerHTML = `Are you sure you want to delete the election <strong>${electionTitle}</strong>?<br><br>
     This action cannot be undone and will remove all votes and data associated with this election.`;

  const confirmBtn = document.getElementById("confirmDeleteElectionBtn");
  confirmBtn.onclick = function () {
    deleteElection(electionId);
  };

  const deleteModal = new bootstrap.Modal(
    document.getElementById("deleteElectionModal")
  );
  deleteModal.show();
}

function deleteElection(electionId) {
  fetch(`/admin/election/delete/${electionId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        const deleteModal = bootstrap.Modal.getInstance(
          document.getElementById("deleteElectionModal")
        );
        deleteModal.hide();
        showAlert("Election deleted successfully", "success");
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        showAlert(data.error || "Failed to delete election", "danger");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showAlert("An error occurred while deleting the election", "danger");
    });
}

function showAlert(message, type = "info") {
  const alertDiv = document.createElement("div");
  alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
  alertDiv.style.zIndex = "9999";
  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;

  document.body.appendChild(alertDiv);

  setTimeout(() => {
    const bsAlert = new bootstrap.Alert(alertDiv);
    bsAlert.close();
  }, 5000);
}

function confirmDeleteCandidate(candidateId, candidateName) {
  // Create modal if it doesn't exist
  if (!document.getElementById("deleteCandidateModal")) {
    const modalHtml = `
      <div class="modal fade" id="deleteCandidateModal" tabindex="-1">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Confirm Deletion</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="deleteCandidateModalBody">
              Are you sure you want to delete this candidate?
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
              <button type="button" class="btn btn-danger" id="confirmDeleteCandidateBtn">Delete Candidate</button>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML("beforeend", modalHtml);
  }

  document.getElementById(
    "deleteCandidateModalBody"
  ).innerHTML = `Are you sure you want to delete the candidate <strong>${candidateName}</strong>?<br><br>
     This action cannot be undone and may affect elections that include this candidate.`;

  const confirmBtn = document.getElementById("confirmDeleteCandidateBtn");
  confirmBtn.onclick = function () {
    deleteCandidate(candidateId);
  };

  const deleteModal = new bootstrap.Modal(
    document.getElementById("deleteCandidateModal")
  );
  deleteModal.show();
}

function deleteCandidate(candidateId) {
  fetch(`/admin/candidate/delete/${candidateId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        const deleteModal = bootstrap.Modal.getInstance(
          document.getElementById("deleteCandidateModal")
        );
        deleteModal.hide();
        showAlert("Candidate deleted successfully", "success");
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        showAlert(data.error || "Failed to delete candidate", "danger");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showAlert("An error occurred while deleting the candidate", "danger");
    });
}

function viewVoter(voterId) {
  window.location.href = `/admin/voter/view/${voterId}`;
}

function confirmDeleteVoter(voterId, voterName) {
  document.getElementById(
    "deleteVoterModalBody"
  ).innerHTML = `Are you sure you want to delete the voter <strong>${voterName}</strong>?<br><br>
     This action cannot be undone and will remove all voting history associated with this voter.`;

  const confirmBtn = document.getElementById("confirmDeleteVoterBtn");
  confirmBtn.onclick = function () {
    deleteVoter(voterId);
  };

  const deleteModal = new bootstrap.Modal(
    document.getElementById("deleteVoterModal")
  );
  deleteModal.show();
}
function deleteVoter(voterId) {
  fetch(`/admin/voter/delete/${voterId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        const deleteModal = bootstrap.Modal.getInstance(
          document.getElementById("deleteVoterModal")
        );
        deleteModal.hide();
        showAlert("Voter deleted successfully", "success");

        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        showAlert(data.error || "Failed to delete voter", "danger");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showAlert("An error occurred while deleting the voter", "danger");
    });
}

function manageCandidates(electionId) {
  // Show the modal
  const modal = new bootstrap.Modal(
    document.getElementById("manageCandidatesModal")
  );
  modal.show();

  // Set the election ID in the hidden field
  document.getElementById("electionId").value = electionId;

  // Show loading, hide form and error
  document.getElementById("candidatesLoading").style.display = "block";
  document.getElementById("manageCandidatesForm").style.display = "none";
  document.getElementById("candidatesError").style.display = "none";

  // Fetch candidates data
  fetch(`/api/election/${electionId}/candidates`)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to load candidates");
      }
      return response.json();
    })
    .then((data) => {
      // Hide loading, show form
      document.getElementById("candidatesLoading").style.display = "none";
      document.getElementById("manageCandidatesForm").style.display = "block";

      // Update modal title
      document.getElementById(
        "manageCandidatesModalLabel"
      ).textContent = `Manage Candidates for ${data.election.title}`;

      // Clear previous candidates
      const candidatesList = document.getElementById("candidatesList");
      candidatesList.innerHTML = "";

      // Add candidates to the list
      if (data.all_candidates && data.all_candidates.length > 0) {
        data.all_candidates.forEach((candidate) => {
          const isChecked = data.selected_candidate_ids.includes(candidate._id)
            ? "checked"
            : "";
          const candidateHtml = `
            <div class="form-check">
              <input class="form-check-input" type="checkbox" name="candidates" 
                     value="${candidate._id}" id="modalCandidate${
            candidate._id
          }"
                     ${isChecked}>
              <label class="form-check-label" for="modalCandidate${
                candidate._id
              }">
                ${candidate.name} - ${candidate.party}
                <small class="text-muted">(${candidate.position || ""})</small>
              </label>
            </div>
          `;
          candidatesList.insertAdjacentHTML("beforeend", candidateHtml);
        });
      } else {
        candidatesList.innerHTML = `
          <div class="alert alert-warning">
            No candidates available. Please 
            <a href="/admin/candidate/add" class="alert-link">add candidates</a> first.
          </div>
        `;
        document.getElementById("saveCandidatesBtn").disabled = true;
      }
    })
    .catch((error) => {
      // Show error message
      document.getElementById("candidatesLoading").style.display = "none";
      const errorElement = document.getElementById("candidatesError");
      errorElement.textContent =
        error.message || "An error occurred while loading candidates";
      errorElement.style.display = "block";
      console.error("Error:", error);
    });
}

// Add event listener for the save button
document.addEventListener("DOMContentLoaded", function () {
  const saveCandidatesBtn = document.getElementById("saveCandidatesBtn");
  if (saveCandidatesBtn) {
    saveCandidatesBtn.addEventListener("click", function () {
      updateElectionCandidates();
    });
  }
});

function updateElectionCandidates() {
  // Get selected candidates
  const checkboxes = document.querySelectorAll(
    '#candidatesList input[name="candidates"]:checked'
  );
  if (checkboxes.length === 0) {
    alert("Please select at least one candidate");
    return;
  }

  // Get election ID
  const electionId = document.getElementById("electionId").value;

  // Collect candidate IDs
  const candidateIds = Array.from(checkboxes).map((checkbox) => checkbox.value);

  // Show loading state
  const saveBtn = document.getElementById("saveCandidatesBtn");
  const originalText = saveBtn.textContent;
  saveBtn.disabled = true;
  saveBtn.innerHTML =
    '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

  // Send update request
  fetch(`/api/election/${electionId}/update_candidates`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ candidates: candidateIds }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to update candidates");
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        // Close modal
        bootstrap.Modal.getInstance(
          document.getElementById("manageCandidatesModal")
        ).hide();

        // Show success message
        showAlert("Candidates updated successfully", "success");

        // Reload page after a short delay
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        throw new Error(data.error || "Failed to update candidates");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showAlert(
        error.message || "An error occurred while updating candidates",
        "danger"
      );

      // Reset button
      saveBtn.disabled = false;
      saveBtn.textContent = originalText;
    });
}

// Enable Bootstrap tooltips
document.addEventListener("DOMContentLoaded", function () {
  var tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Candidate selection in voting page
  const candidateCards = document.querySelectorAll(".candidate-card");
  const candidateRadios = document.querySelectorAll(
    'input[name="candidate_id"]'
  );

  candidateRadios.forEach((radio) => {
    radio.addEventListener("change", function () {
      // Remove selected class from all cards
      candidateCards.forEach((card) => {
        card.classList.remove("selected-candidate");
      });

      // Add selected class to the chosen card
      if (this.checked) {
        const selectedCard = this.closest(".candidate-card");
        if (selectedCard) {
          selectedCard.classList.add("selected-candidate");
        }
      }
    });
  });
});

function resetVoterPassword(voterId, voterName) {
  // Create modal if it doesn't exist
  if (!document.getElementById("passwordResetModal")) {
    const modalHtml = `
      <div class="modal fade" id="passwordResetModal" tabindex="-1" aria-labelledby="passwordResetModalLabel" aria-hidden="true">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="passwordResetModalLabel">Password Reset</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
              <div id="passwordResetLoading" class="text-center">
                <div class="spinner-border text-primary" role="status">
                  <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Resetting password...</p>
              </div>
              <div id="passwordResetError" class="alert alert-danger" style="display: none;"></div>
              <div id="passwordResetSuccess" style="display: none;">
                <div class="alert alert-success">
                  <i class="fas fa-check-circle"></i> Password has been reset successfully.
                </div>
                <div class="mb-3">
                  <label class="form-label">Temporary Password:</label>
                  <div class="input-group">
                    <input type="text" class="form-control" id="tempPassword" readonly>
                    <button class="btn btn-outline-secondary" type="button" onclick="copyPassword()">
                      <i class="fas fa-copy"></i> Copy
                    </button>
                  </div>
                  <div class="form-text text-warning">
                    <i class="fas fa-exclamation-triangle"></i> 
                    Please provide this temporary password to the voter. They should change it after logging in.
                  </div>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML("beforeend", modalHtml);
  }

  // Show modal
  const modal = new bootstrap.Modal(
    document.getElementById("passwordResetModal")
  );
  modal.show();

  // Show loading, hide other sections
  document.getElementById("passwordResetLoading").style.display = "block";
  document.getElementById("passwordResetError").style.display = "none";
  document.getElementById("passwordResetSuccess").style.display = "none";

  // Update modal title
  document.getElementById(
    "passwordResetModalLabel"
  ).textContent = `Reset Password for ${voterName}`;

  // Send reset request
  fetch(`/admin/voter/reset_password/${voterId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Failed to reset password");
      }
      return response.json();
    })
    .then((data) => {
      // Hide loading
      document.getElementById("passwordResetLoading").style.display = "none";

      if (data.success) {
        // Show success message and temporary password
        document.getElementById("passwordResetSuccess").style.display = "block";
        document.getElementById("tempPassword").value = data.temp_password;
      } else {
        throw new Error(data.error || "Unknown error");
      }
    })
    .catch((error) => {
      // Show error message
      document.getElementById("passwordResetLoading").style.display = "none";
      const errorElement = document.getElementById("passwordResetError");
      errorElement.textContent =
        error.message || "An error occurred while resetting the password";
      errorElement.style.display = "block";
      console.error("Error:", error);
    });
}

function copyPassword() {
  const tempPasswordField = document.getElementById("tempPassword");
  tempPasswordField.select();
  document.execCommand("copy");

  // Show copied message
  const button = document.querySelector("#tempPassword + button");
  const originalText = button.innerHTML;
  button.innerHTML = '<i class="fas fa-check"></i> Copied!';

  // Reset button text after 2 seconds
  setTimeout(() => {
    button.innerHTML = originalText;
  }, 2000);
}
