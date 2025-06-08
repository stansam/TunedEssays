// class PaymentManager {
//     constructor() {
//         this.dropinInstance = null;
//         this.clientToken = null;
//         this.isProcessing = false;
//     }

//     // Initialize payment form
//     async init(clientToken, orderId, orderAmount) {
//         this.clientToken = clientToken;
//         this.orderId = orderId;
//         this.orderAmount = orderAmount;

//         try {
//             await this.createDropin();
//             this.bindEvents();
//         } catch (error) {
//             console.error('Payment initialization failed:', error);
//             this.showError('Failed to initialize payment form. Please refresh the page.');
//         }
//     }

//     // Create Braintree Drop-in
//     createDropin() {
//         return new Promise((resolve, reject) => {
//             braintree.dropin.create({
//                 authorization: this.clientToken,
//                 container: '#dropin-container',
//                 paypal: {
//                     flow: 'checkout',
//                     amount: this.orderAmount,
//                     currency: 'USD',
//                     displayName: 'Paper Writing Service'
//                 },
//                 applePay: {
//                     displayName: 'Paper Writing Service',
//                     paymentRequest: {
//                         total: {
//                             label: 'Paper Writing Service',
//                             amount: this.orderAmount
//                         }
//                     }
//                 },
//                 googlePay: {
//                     merchantId: 'your-merchant-id', // Replace with actual merchant ID
//                     paymentDataRequest: {
//                         transactionInfo: {
//                             totalPriceStatus: 'FINAL',
//                             totalPrice: this.orderAmount.toString(),
//                             currencyCode: 'USD'
//                         }
//                     }
//                 },
//                 card: {
//                     cardholderName: {
//                         required: true
//                     }
//                 }
//             }, (createErr, instance) => {
//                 if (createErr) {
//                     reject(createErr);
//                     return;
//                 }
                
//                 this.dropinInstance = instance;
//                 this.enableSubmitButton();
//                 resolve(instance);
//             });
//         });
//     }

//     // Bind event listeners
//     bindEvents() {
//         const submitButton = document.getElementById('submit-button');
//         if (submitButton) {
//             submitButton.addEventListener('click', (e) => this.handleSubmit(e));
//         }

//         // Payment method selection
//         const methodInputs = document.querySelectorAll('input[name="payment-method"]');
//         methodInputs.forEach(input => {
//             input.addEventListener('change', () => this.handleMethodChange());
//         });
//     }

//     // Handle payment method change
//     handleMethodChange() {
//         const selectedMethod = document.querySelector('input[name="payment-method"]:checked').value;
//         // You can add specific logic for different payment methods here
//         console.log('Payment method changed to:', selectedMethod);
//     }

//     // Handle form submission
//     async handleSubmit(event) {
//         event.preventDefault();
        
//         if (this.isProcessing) {
//             return;
//         }

//         if (!this.dropinInstance) {
//             this.showError('Payment form not ready. Please wait or refresh the page.');
//             return;
//         }

//         this.setProcessingState(true);
//         this.clearMessages();

//         try {
//             const payload = await this.getPaymentMethod();
//             const result = await this.processPayment(payload);
            
//             if (result.success) {
//                 this.showSuccess('Payment processed successfully! Redirecting...');
//                 setTimeout(() => {
//                     window.location.href = `/payment/success/${result.payment_id}`;
//                 }, 2000);
//             } else {
//                 this.showError(result.error || 'Payment failed. Please try again.');
//                 this.setProcessingState(false);
//             }
//         } catch (error) {
//             console.error('Payment processing error:', error);
//             this.showError('Payment processing failed. Please try again.');
//             this.setProcessingState(false);
//         }
//     }

//     // Get payment method from Drop-in
//     getPaymentMethod() {
//         return new Promise((resolve, reject) => {
//             this.dropinInstance.requestPaymentMethod((err, payload) => {
//                 if (err) {
//                     reject(err);
//                 } else {
//                     resolve(payload);
//                 }
//             });
//         });
//     }

//     // Process payment on server
//     async processPayment(payload) {
//         const selectedMethod = document.querySelector('input[name="payment-method"]:checked').value;
        
//         const response = await fetch('/payment/process', {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//                 'X-Requested-With': 'XMLHttpRequest'
//             },
//             body: JSON.stringify({
//                 order_id: this.orderId,
//                 payment_method_nonce: payload.nonce,
//                 payment_method: selectedMethod,
//                 device_data: payload.deviceData || null
//             })
//         });

//         if (!response.ok) {
//             throw new Error(`HTTP error! status: ${response.status}`);
//         }

//         return await response.json();
//     }

//     // Set processing state
//     setProcessingState(isProcessing) {
//         this.isProcessing = isProcessing;
//         const submitButton = document.getElementById('submit-button');
//         const normalText = submitButton.querySelector('.normal-text');
//         const loadingText = submitButton.querySelector('.loading');
        
//         if (isProcessing) {
//             submitButton.disabled = true;
//             normalText.style.display = 'none';
//             loadingText.style.display = 'inline';
//         } else {
//             submitButton.disabled = false;
//             normalText.style.display = 'inline';
//             loadingText.style.display = 'none';
//         }
//     }

//     // Enable submit button
//     enableSubmitButton() {
//         const submitButton = document.getElementById('submit-button');
//         if (submitButton) {
//             submitButton.disabled = false;
//         }
//     }

//     // Show error message
//     showError(message) {
//         const errorDiv = document.getElementById('error-message');
//         if (errorDiv) {
//             errorDiv.textContent = message;
//             errorDiv.style.display = 'block';
//             errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
//         }
//     }

//     // Show success message
//     showSuccess(message) {
//         const successDiv = document.getElementById('success-message');
//         if (successDiv) {
//             successDiv.textContent = message;
//             successDiv.style.display = 'block';
//             successDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
//         }
//     }

//     // Clear messages
//     clearMessages() {
//         const errorDiv = document.getElementById('error-message');
//         const successDiv = document.getElementById('success-message');
        
//         if (errorDiv) errorDiv.style.display = 'none';
//         if (successDiv) successDiv.style.display = 'none';
//     }
// }

// // Payment status checker
// class PaymentStatusChecker {
//     constructor(paymentId) {
//         this.paymentId = paymentId;
//         this.checkInterval = null;
//         this.maxChecks = 20; // Maximum number of status checks
//         this.currentCheck = 0;
//     }

//     // Start checking payment status
//     startChecking() {
//         this.checkInterval = setInterval(() => {
//             this.checkStatus();
//         }, 3000); // Check every 3 seconds
//     }

//     // Stop checking
//     stopChecking() {
//         if (this.checkInterval) {
//             clearInterval(this.checkInterval);
//             this.checkInterval = null;
//         }
//     }

//     // Check payment status
//     async checkStatus() {
//         this.currentCheck++;
        
//         if (this.currentCheck > this.maxChecks) {
//             this.stopChecking();
//             return;
//         }

//         try {
//             const response = await fetch(`/payment/status/${this.paymentId}`);
//             const data = await response.json();
            
//             if (data.status === 'completed') {
//                 this.stopChecking();
//                 this.onStatusComplete(data);
//             } else if (data.status === 'failed') {
//                 this.stopChecking();
//                 this.onStatusFailed(data);
//             }
//         } catch (error) {
//             console.error('Error checking payment status:', error);
//         }
//     }

//     // Handle completed status
//     onStatusComplete(paymentData) {
//         // Override this method in implementation
//         console.log('Payment completed:', paymentData);
//     }

//     // Handle failed status
//     onStatusFailed(paymentData) {
//         // Override this method in implementation
//         console.log('Payment failed:', paymentData);
//     }
// }

// // Utility functions
// const PaymentUtils = {
//     // Format currency
//     formatCurrency(amount, currency = 'USD') {
//         return new Intl.NumberFormat('en-US', {
//             style: 'currency',
//             currency: currency
//         }).format(amount);
//     },

//     // Validate credit card number (basic)
//     validateCardNumber(number) {
//         const regex = /^[\d\s-]+$/;
//         return regex.test(number) && number.replace(/\D/g, '').length >= 13;
//     },

//     // Get payment method display name
//     getPaymentMethodName(method) {
//         const methods = {
//             'credit_card': 'Credit/Debit Card',
//             'paypal': 'PayPal',
//             'apple_pay': 'Apple Pay',
//             'google_pay': 'Google Pay'
//         };
//         return methods[method] || method;
//     },

//     // Show loading overlay
//     showLoadingOverlay(message = 'Processing...') {
//         const overlay = document.createElement('div');
//         overlay.id = 'payment-loading-overlay';
//         overlay.innerHTML = `
//             <div class="loading-content">
//                 <div class="spinner-border text-primary" role="status">
//                     <span class="visually-hidden">Loading...</span>
//                 </div>
//                 <p class="mt-3">${message}</p>
//             </div>
//         `;
//         overlay.style.cssText = `
//             position: fixed;
//             top: 0;
//             left: 0;
//             width: 100%;
//             height: 100%;
//             background: rgba(0,0,0,0.5);
//             display: flex;
//             justify-content: center;
//             align-items: center;
//             z-index: 9999;
//             color: white;
//             text-align: center;
//         `;
//         document.body.appendChild(overlay);
//     },

//     // Hide loading overlay
//     hideLoadingOverlay() {
//         const overlay = document.getElementById('payment-loading-overlay');
//         if (overlay) {
//             overlay.remove();
//         }
//     },

//     // Copy text to clipboard
//     async copyToClipboard(text) {
//         try {
//             await navigator.clipboard.writeText(text);
//             return true;
//         } catch (err) {
//             // Fallback for older browsers
//             const textArea = document.createElement('textarea');
//             textArea.value = text;
//             document.body.appendChild(textArea);
//             textArea.select();
//             document.execCommand('copy');
//             document.body.removeChild(textArea);
//             return true;
//         }
//     }
// };

// // Export for use in other files
// if (typeof module !== 'undefined' && module.exports) {
//     module.exports = { PaymentManager, PaymentStatusChecker, PaymentUtils };
// }
// Fixed PaymentManager with better error handling and debugging

// class PaymentManager {
//     constructor() {
//         this.dropinInstance = null;
//         this.clientToken = null;
//         this.isProcessing = false;
//     }

//     // Initialize payment form with better error handling
//     async init(clientToken, orderId, orderAmount) {
//         console.log('Initializing PaymentManager with:', { clientToken: clientToken ? 'present' : 'missing', orderId, orderAmount });
//         console.log(clientToken)
        
//         // Validate inputs
//         if (!clientToken) {
//             throw new Error('Invalid or missing client token');
//         }
        
//         if (!orderId || !orderAmount) {
//             throw new Error('Missing order ID or amount');
//         }

//         this.clientToken = clientToken.trim();
//         this.orderId = orderId;
//         this.orderAmount = orderAmount;
//         console.log('Client token details:', {
//             token: this.clientToken,
//             tokenLength: this.clientToken?.length,
//             tokenStart: this.clientToken?.substring(0, 20) + '...',
//             isString: typeof this.clientToken === 'string'
//         });

//         try {
//             await this.createDropin();
//             this.bindEvents();
//             console.log('PaymentManager initialized successfully');
//         } catch (error) {
//             console.error('Payment initialization failed:', error);
//             this.showError('Failed to initialize payment form: ' + error.message);
//             throw error;
//         }
//     }

//     // Create Braintree Drop-in with better configuration
//     createDropin() {
//         return new Promise((resolve, reject) => {
//             // Basic configuration - start with minimal setup
//             const config = {
//                 authorization: this.clientToken,
//                 container: '#dropin-container',
//                 card: {
//                     cardholderName: {
//                         required: true
//                     }
//                 }
//             };

//             // Only add payment methods if they're likely to work
//             // PayPal configuration
//             if (this.orderAmount && this.orderAmount > 0) {
//                 config.paypal = {
//                     flow: 'checkout',
//                     amount: this.orderAmount,
//                     currency: 'USD',
//                     displayName: 'Paper Writing Service'
//                 };
//             }

//             // Apple Pay - only add if supported
//             if (window.ApplePaySession && ApplePaySession.canMakePayments()) {
//                 config.applePay = {
//                     displayName: 'Paper Writing Service',
//                     paymentRequest: {
//                         total: {
//                             label: 'Paper Writing Service',
//                             amount: this.orderAmount.toString()
//                         }
//                     }
//                 };
//             }

//             // Google Pay - only add if you have a valid merchant ID
//             // Comment out or remove if you don't have Google Pay set up
//             /*
//             config.googlePay = {
//                 merchantId: 'your-actual-merchant-id', // Replace with real merchant ID
//                 paymentDataRequest: {
//                     transactionInfo: {
//                         totalPriceStatus: 'FINAL',
//                         totalPrice: this.orderAmount.toString(),
//                         currencyCode: 'USD'
//                     }
//                 }
//             };
//             */

//             console.log('Creating Drop-in with config:', config);

//             braintree.dropin.create(config, (createErr, instance) => {
//                 if (createErr) {
//                     console.error('Drop-in creation error:', createErr);
//                     reject(new Error('Failed to create payment form: ' + createErr.message));
//                     return;
//                 }
                
//                 console.log('Drop-in created successfully');
//                 this.dropinInstance = instance;
//                 this.enableSubmitButton();
//                 resolve(instance);
//             });
//         });
//     }

//     // Bind event listeners
//     bindEvents() {
//         const submitButton = document.getElementById('submit-button');
//         if (submitButton) {
//             submitButton.addEventListener('click', (e) => this.handleSubmit(e));
//         }

//         // Payment method selection
//         const methodInputs = document.querySelectorAll('input[name="payment-method"]');
//         methodInputs.forEach(input => {
//             input.addEventListener('change', () => this.handleMethodChange());
//         });
//     }

//     // Handle payment method change
//     handleMethodChange() {
//         const selectedMethod = document.querySelector('input[name="payment-method"]:checked');
//         if (selectedMethod) {
//             console.log('Payment method changed to:', selectedMethod.value);
//         }
//     }

//     // Handle form submission with better error handling
//     async handleSubmit(event) {
//         event.preventDefault();
        
//         if (this.isProcessing) {
//             console.log('Already processing payment');
//             return;
//         }

//         if (!this.dropinInstance) {
//             this.showError('Payment form not ready. Please wait or refresh the page.');
//             return;
//         }

//         this.setProcessingState(true);
//         this.clearMessages();

//         try {
//             console.log('Getting payment method...');
//             const payload = await this.getPaymentMethod();
//             console.log('Payment method obtained:', payload.type);
            
//             console.log('Processing payment...');
//             const result = await this.processPayment(payload);
            
//             if (result.success) {
//                 this.showSuccess('Payment processed successfully! Redirecting...');
//                 setTimeout(() => {
//                     window.location.href = `/payment/success/${result.payment_id}`;
//                 }, 2000);
//             } else {
//                 console.error('Payment failed:', result);
//                 this.showError(result.error || 'Payment failed. Please try again.');
//                 this.setProcessingState(false);
//             }
//         } catch (error) {
//             console.error('Payment processing error:', error);
//             this.showError('Payment processing failed: ' + error.message);
//             this.setProcessingState(false);
//         }
//     }

//     // Get payment method from Drop-in
//     getPaymentMethod() {
//         return new Promise((resolve, reject) => {
//             this.dropinInstance.requestPaymentMethod((err, payload) => {
//                 if (err) {
//                     console.error('Error getting payment method:', err);
//                     reject(new Error('Failed to get payment method: ' + err.message));
//                 } else {
//                     resolve(payload);
//                 }
//             });
//         });
//     }

//     // Process payment on server with better error handling
//     async processPayment(payload) {
//         const selectedMethodElement = document.querySelector('input[name="payment-method"]:checked');
//         const selectedMethod = selectedMethodElement ? selectedMethodElement.value : 'credit_card';
        
//         const requestData = {
//             order_id: this.orderId,
//             payment_method_nonce: payload.nonce,
//             payment_method: selectedMethod,
//             device_data: payload.deviceData || null
//         };

//         console.log('Sending payment request:', requestData);

//         const headers = {
//             'Content-Type': 'application/json',
//             'X-Requested-With': 'XMLHttpRequest'
//         };

//         // Add CSRF token if available
//         const csrfToken = this.getCSRFToken();
//         if (csrfToken) {
//             headers['X-CSRFToken'] = csrfToken;
//         }

//         const response = await fetch('/payment/process', {
//             method: 'POST',
//             headers: headers,
//             body: JSON.stringify(requestData)
//         });

//         if (!response.ok) {
//             const errorText = await response.text();
//             console.error('Server error:', response.status, errorText);
//             throw new Error(`Server error: ${response.status} - ${errorText}`);
//         }

//         const result = await response.json();
//         console.log('Payment response:', result);
//         return result;
//     }

//     // Get CSRF token safely
//     getCSRFToken() {
//         // Try multiple methods to get CSRF token
//         const tokenMeta = document.querySelector('meta[name="csrf-token"]');
//         if (tokenMeta) {
//             return tokenMeta.getAttribute('content');
//         }

//         const tokenInput = document.querySelector('input[name="csrf_token"]');
//         if (tokenInput) {
//             return tokenInput.value;
//         }

//         // Fallback to template variable if available
//         // if (typeof csrfToken !== 'undefined' && csrfToken !== '{{ csrf_token() }}') {
//         //     return csrfToken;
//         // }

//         return null;
//     }

//     // Set processing state
//     setProcessingState(isProcessing) {
//         this.isProcessing = isProcessing;
//         const submitButton = document.getElementById('submit-button');
//         if (!submitButton) return;

//         const normalText = submitButton.querySelector('.normal-text');
//         const loadingText = submitButton.querySelector('.loading');
        
//         if (isProcessing) {
//             submitButton.disabled = true;
//             if (normalText) normalText.style.display = 'none';
//             if (loadingText) loadingText.style.display = 'inline';
//         } else {
//             submitButton.disabled = false;
//             if (normalText) normalText.style.display = 'inline';
//             if (loadingText) loadingText.style.display = 'none';
//         }
//     }

//     // Enable submit button
//     enableSubmitButton() {
//         const submitButton = document.getElementById('submit-button');
//         if (submitButton) {
//             submitButton.disabled = false;
//             console.log('Submit button enabled');
//         }
//     }

//     // Show error message
//     showError(message) {
//         console.error('Payment error:', message);
//         const errorDiv = document.getElementById('error-message');
//         if (errorDiv) {
//             errorDiv.textContent = message;
//             errorDiv.style.display = 'block';
//             errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
//         }
//     }

//     // Show success message
//     showSuccess(message) {
//         console.log('Payment success:', message);
//         const successDiv = document.getElementById('success-message');
//         if (successDiv) {
//             successDiv.textContent = message;
//             successDiv.style.display = 'block';
//             successDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
//         }
//     }

//     // Clear messages
//     clearMessages() {
//         const errorDiv = document.getElementById('error-message');
//         const successDiv = document.getElementById('success-message');
        
//         if (errorDiv) errorDiv.style.display = 'none';
//         if (successDiv) successDiv.style.display = 'none';
//     }
// }

// // Debugging helper
// function debugPaymentSetup() {
//     console.log('=== Payment Debug Info ===');
//     console.log('Braintree loaded:', typeof braintree !== 'undefined');
//     console.log('Drop-in available:', typeof braintree?.dropin !== 'undefined');
//     console.log('Client token element:', document.querySelector('script:contains("clientToken")'));
//     console.log('Drop-in container:', document.getElementById('dropin-container'));
//     console.log('Submit button:', document.getElementById('submit-button'));
//     console.log('Payment method radios:', document.querySelectorAll('input[name="payment-method"]').length);
    
//     // Check for template variables
//     const scripts = document.querySelectorAll('script');
//     scripts.forEach(script => {
//         if (script.textContent.includes('clientToken')) {
//             console.log('Found clientToken script:', script.textContent.substring(0, 200) + '...');
//         }
//     });
// }

// // Run debug on page load
// if (typeof window !== 'undefined') {
//     window.debugPaymentSetup = debugPaymentSetup;
// }

class PaymentManager {
    constructor() {
        this.dropinInstance = null;
        this.clientToken = null;
        this.isProcessing = false;
    }

    // Initialize payment form with better error handling
    async init(clientToken, orderId, orderAmount) {
        console.log('Initializing PaymentManager with:', { 
            clientToken: clientToken ? 'present' : 'missing', 
            orderId, 
            orderAmount 
        });
        
        // Validate inputs more thoroughly
        if (!clientToken || typeof clientToken !== 'string' || clientToken.trim() === '') {
            throw new Error('Invalid or missing client token');
        }
        
        if (!orderId) {
            throw new Error('Order ID is required');
        }
        
        if (!orderAmount || orderAmount <= 0) {
            throw new Error('Order amount must be greater than 0');
        }
        // if (!orderNumber || typeof orderNumber !== 'string' || orderNumber.trim() === '') {
        //     throw new Error('Order number not assigned or invalid');
        // }

        this.clientToken = clientToken.trim();
        this.orderId = orderId;
        this.orderAmount = parseFloat(orderAmount);
        // this.orderNumber = orderNumber;
        
        console.log('Validated inputs:', {
            tokenLength: this.clientToken.length,
            orderId: this.orderId,
            orderAmount: this.orderAmount
        });

        try {
            await this.createDropin();
            this.bindEvents();
            console.log('PaymentManager initialized successfully');
        } catch (error) {
            console.error('Payment initialization failed:', error);
            this.showError('Failed to initialize payment form: ' + error.message);
            throw error;
        }
    }

    // Create Braintree Drop-in with better configuration
    createDropin() {
        return new Promise((resolve, reject) => {
            // Validate Braintree is loaded
            if (typeof braintree === 'undefined' || !braintree.dropin) {
                reject(new Error('Braintree SDK not loaded properly'));
                return;
            }
            // var deviceDataInput = form['device_data'];

            // Basic configuration
            const config = {
                authorization: this.clientToken,
                container: '#dropin-container',
                dataCollector: true,
                card: {
                    cardholderName: {
                        required: true
                    }
                }
            };

            // PayPal configuration - only if amount is valid
            if (this.orderAmount && this.orderAmount > 0) {
                config.paypal = {
                    flow: 'checkout',
                    amount: this.orderAmount.toFixed(2),
                    currency: 'USD',
                    displayName: 'Paper Writing Service'
                };
            }

            if (this.orderAmount && this.orderAmount > 0) {
                config.venmo = {
                    allowDesktop: true, // Enables Venmo on desktop via QR code
                    // Note: Venmo will only appear if the user is on a mobile device with Venmo app
                    // or if allowDesktop is true (shows QR code for desktop users)
                };
            }

            // Apple Pay - only add if supported
            if (window.ApplePaySession && ApplePaySession.canMakePayments()) {
                config.applePay = {
                    displayName: 'Paper Writing Service',
                    paymentRequest: {
                        total: {
                            label: 'Paper Writing Service',
                            amount: this.orderAmount.toFixed(2)
                        }
                    }
                };
            }

            console.log('Creating Drop-in with config:', config);

            braintree.dropin.create(config, (createErr, instance) => {
                if (createErr) {
                    console.error('Drop-in creation error:', createErr);
                    reject(new Error(`Failed to create payment form: ${createErr.message}`));
                    return;
                }
                // if (deviceDataInput == null) {
                //     deviceDataInput = document.createElement('input');
                //     deviceDataInput.name = 'device_data';
                //     deviceDataInput.type = 'hidden';
                //     form.appendChild(deviceDataInput);
                // }
                
                console.log('Drop-in created successfully');
                this.dropinInstance = instance;
                this.enableSubmitButton();
                resolve(instance);
            });
        });
    }

    // Bind event listeners
    bindEvents() {
        const submitButton = document.getElementById('submit-button');
        if (submitButton) {
            submitButton.addEventListener('click', (e) => this.handleSubmit(e));
        } else {
            console.warn('Submit button not found');
        }

        // Payment method selection
        const methodInputs = document.querySelectorAll('input[name="payment-method"]');
        methodInputs.forEach(input => {
            input.addEventListener('change', () => this.handleMethodChange());
        });
    }

    // Handle payment method change
    handleMethodChange() {
        const selectedMethod = document.querySelector('input[name="payment-method"]:checked');
        if (selectedMethod) {
            console.log('Payment method changed to:', selectedMethod.value);
        }
    }

    // Handle form submission with better error handling
    async handleSubmit(event) {
        event.preventDefault();
        
        if (this.isProcessing) {
            console.log('Already processing payment');
            return;
        }

        if (!this.dropinInstance) {
            this.showError('Payment form not ready. Please wait or refresh the page.');
            return;
        }

        this.setProcessingState(true);
        this.clearMessages();

        try {
            console.log('Getting payment method...');
            const payload = await this.getPaymentMethod();
            console.log('Payment method obtained:', payload.type);
            
            // Validate payload
            if (!payload.nonce) {
                throw new Error('Invalid payment method - no nonce received');
            }
            
            console.log('Processing payment...');
            const result = await this.processPayment(payload);
            
            if (result.success) {
                this.showSuccess('Payment processed successfully! Redirecting...');
                setTimeout(() => {
                    window.location.href = `/payment/success/${result.payment_id}`;
                }, 2000);
            } else {
                console.error('Payment failed:', result);
                this.showError(result.error || 'Payment failed. Please try again.');
                this.setProcessingState(false);
            }
        } catch (error) {
            console.error('Payment processing error:', error);
            this.showError('Payment processing failed: ' + error.message);
            this.setProcessingState(false);
        }
    }

    // Get payment method from Drop-in
    getPaymentMethod() {
        return new Promise((resolve, reject) => {
            this.dropinInstance.requestPaymentMethod((err, payload) => {
                if (err) {
                    console.error('Error getting payment method:', err);
                    reject(new Error(`Failed to get payment method: ${err.message}`));
                } else {
                    console.log('Payment method payload:', payload);
                    resolve(payload);
                }
            });
        });
    }

    // Process payment on server with better error handling
    async processPayment(payload) {
        const selectedMethodElement = document.querySelector('input[name="payment-method"]:checked');
        const selectedMethod = selectedMethodElement ? selectedMethodElement.value : 'credit_card';
        
        // Validate required data
        if (!this.orderId) {
            throw new Error('Order ID is missing');
        }
        
        if (!payload.nonce) {
            throw new Error('Payment nonce is missing');
        }
        
        const requestData = {
            order_id: parseInt(this.orderId),
            payment_method_nonce: payload.nonce,
            payment_method: selectedMethod,
            device_data: payload.deviceData || null
        };

        console.log('Sending payment request:', requestData);

        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };

        // Add CSRF token if available
        const csrfToken = this.getCSRFToken();
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        try {
            const response = await fetch('/payment/process', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(requestData)
            });

            // Handle different response types for better debugging
            let responseData;
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('application/json')) {
                responseData = await response.json();
            } else {
                const textResponse = await response.text();
                console.error('Non-JSON response:', textResponse);
                throw new Error(`Server returned non-JSON response: ${response.status}`);
            }

            if (!response.ok) {
                console.error('Server error:', response.status, responseData);
                throw new Error(responseData.error || `Server error: ${response.status}`);
            }

            console.log('Payment response:', responseData);
            return responseData;
            
        } catch (error) {
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('Network error - please check your connection');
            }
            throw error;
        }
    }

    // Get CSRF token safely
    getCSRFToken() {
        // Try multiple methods to get CSRF token
        const tokenMeta = document.querySelector('meta[name="csrf-token"]');
        if (tokenMeta) {
            return tokenMeta.getAttribute('content');
        }

        const tokenInput = document.querySelector('input[name="csrf_token"]');
        if (tokenInput) {
            return tokenInput.value;
        }

        // Check for Flask-WTF token
        const flaskToken = document.querySelector('input[name="csrf_token"]');
        if (flaskToken) {
            return flaskToken.value;
        }

        return null;
    }

    // Set processing state
    setProcessingState(isProcessing) {
        this.isProcessing = isProcessing;
        const submitButton = document.getElementById('submit-button');
        if (!submitButton) return;

        const normalText = submitButton.querySelector('.normal-text');
        const loadingText = submitButton.querySelector('.loading');
        
        if (isProcessing) {
            submitButton.disabled = true;
            if (normalText) normalText.style.display = 'none';
            if (loadingText) loadingText.style.display = 'inline';
        } else {
            submitButton.disabled = false;
            if (normalText) normalText.style.display = 'inline';
            if (loadingText) loadingText.style.display = 'none';
        }
    }

    // Enable submit button
    enableSubmitButton() {
        const submitButton = document.getElementById('submit-button');
        if (submitButton) {
            submitButton.disabled = false;
            console.log('Submit button enabled');
        }
    }

    // Show error message
    showError(message) {
        console.error('Payment error:', message);
        const errorDiv = document.getElementById('error-message');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            // Fallback to alert if no error div
            alert('Payment Error: ' + message);
        }
    }

    // Show success message
    showSuccess(message) {
        console.log('Payment success:', message);
        const successDiv = document.getElementById('success-message');
        if (successDiv) {
            successDiv.textContent = message;
            successDiv.style.display = 'block';
            successDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    // Clear messages
    clearMessages() {
        const errorDiv = document.getElementById('error-message');
        const successDiv = document.getElementById('success-message');
        
        if (errorDiv) errorDiv.style.display = 'none';
        if (successDiv) successDiv.style.display = 'none';
    }
}

// Enhanced debugging helper
function debugPaymentSetup() {
    console.log('=== Payment Debug Info ===');
    console.log('Braintree loaded:', typeof braintree !== 'undefined');
    console.log('Drop-in available:', typeof braintree?.dropin !== 'undefined');
    console.log('Drop-in container:', document.getElementById('dropin-container'));
    console.log('Submit button:', document.getElementById('submit-button'));
    console.log('Payment method radios:', document.querySelectorAll('input[name="payment-method"]').length);
    console.log('Error message div:', document.getElementById('error-message'));
    console.log('Success message div:', document.getElementById('success-message'));
    
    // Check CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]') || 
                     document.querySelector('input[name="csrf_token"]');
    console.log('CSRF token found:', !!csrfToken);
    
    // Check for template variables
    const scripts = document.querySelectorAll('script');
    scripts.forEach(script => {
        if (script.textContent.includes('clientToken')) {
            console.log('Found clientToken script');
        }
    });
}

// Run debug on page load
if (typeof window !== 'undefined') {
    window.debugPaymentSetup = debugPaymentSetup;
}