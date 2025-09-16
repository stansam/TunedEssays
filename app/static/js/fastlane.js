class FastlaneCheckout {
    constructor() {
        this.fastlaneInstance = null;
        this.customerContextId = null;
        this.isGuestCustomer = true;
        this.shippingAddress = null;
        this.paymentToken = null;
        this.orderData = window.orderData || {};
        this.clientTokenData = null;
        
        // DOM elements
        this.paymentSection = document.getElementById('payment-section');
        this.paypalButtonContainer = document.getElementById('paypal-button-container');
        this.errorMessage = document.getElementById('error-message');
        this.successMessage = document.getElementById('success-message');
        this.loadingOverlay = document.getElementById('payment-loading-overlay');
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    /**
     * Initialize Fastlane checkout
     */
    async init() {
        try {
            this.showLoading('Initializing secure checkout...');
            
            // Get client token from backend
            const clientTokenResponse = await this.fetchClientToken();
            if (!clientTokenResponse.success) {
                throw new Error(clientTokenResponse.error || 'Failed to get client token');
            }
            
            this.clientTokenData = clientTokenResponse.data;
            
            // Initialize Fastlane
            await this.initializeFastlane();
            
            // Setup checkout form
            this.setupCheckoutForm();
            
            this.hideLoading();
            this.showSuccess('Secure checkout ready');
            
        } catch (error) {
            console.error('Fastlane initialization error:', error);
            this.hideLoading();
            // this.showError(`Initialization failed: ${error.message}`);
            
            // Fallback to standard PayPal buttons if Fastlane fails
            this.initializeFallbackPayPal();
        }
    }

    /**
     * Fetch client token from backend
     */
    async fetchClientToken() {
        try {
            const response = await fetch('/payment/api/client-token', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCSRFToken()
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.error) {
                return { success: false, error: data.error };
            }

            return { success: true, data };
            
        } catch (error) {
            console.error('Error fetching client token:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Initialize PayPal Fastlane SDK
     */
    async initializeFastlane() {
        if (!this.clientTokenData) {
            throw new Error('Client token data not available');
        }

        // Initialize Fastlane
        window.localStorage.setItem("fastlaneEnv", "sandbox");
        
        this.fastlaneInstance = await window.paypal.Fastlane();
        this.fastlaneInstance.setLocale('en_us');
        

        console.log('Fastlane initialized successfully');
    }

    /**
     * Collect device data for fraud prevention
     */
    async collectDeviceData() {
        try {
            // Collect basic device information
            const deviceData = {
                userAgent: navigator.userAgent,
                screenResolution: `${screen.width}x${screen.height}`,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                language: navigator.language,
                timestamp: new Date().toISOString()
            };

            return JSON.stringify(deviceData);
        } catch (error) {
            console.warn('Error collecting device data:', error);
            return JSON.stringify({ timestamp: new Date().toISOString() });
        }
    }

    /**
     * Setup checkout form with Fastlane components
     */
    setupCheckoutForm() {
        // Create checkout form container
        const checkoutForm = this.createCheckoutForm();
        
        // Replace PayPal button container with Fastlane form
        if (this.paypalButtonContainer) {
            this.paypalButtonContainer.innerHTML = '';
            this.paypalButtonContainer.appendChild(checkoutForm);
        }
    }

    /**
     * Create comprehensive checkout form
     */
    createCheckoutForm() {
        const form = document.createElement('form');
        form.id = 'checkout-form';
        form.className = 'fastlane-checkout-form';

        form.innerHTML = `
            <!-- Customer Identification Section -->
            <section id="customer-section" class="active">
                <div class="section-header">
                    <h4>Contact Information</h4>
                    <button type="button" class="edit-button" id="edit-customer" style="display: none;">Edit</button>
                </div>
                <div class="section-content">
                    <div class="form-group">
                        <label for="customer-email">Email Address *</label>
                        <input type="email" id="customer-email" class="form-control" required 
                               placeholder="Enter your email address">
                    </div>
                    <button type="button" id="continue-customer" class="btn btn-primary">
                        Continue to Shipping
                    </button>
                </div>
                <div class="summary" id="customer-summary" style="display: none;"></div>
            </section>

            <!-- Shipping Section -->
            <section id="shipping-section">
                <div class="section-header">
                    <h4>Shipping Information</h4>
                    <button type="button" class="edit-button" id="edit-shipping" style="display: none;">Edit</button>
                </div>
                <div class="section-content">
                    <div id="shipping-component"></div>
                    <button type="button" id="continue-shipping" class="btn btn-primary" style="display: none;">
                        Continue to Payment
                    </button>
                </div>
                <div class="summary" id="shipping-summary" style="display: none;"></div>
            </section>

            <!-- Payment Section -->
            <section id="payment-section-form">
                <div class="section-header">
                    <h4>Payment Information</h4>
                    <button type="button" class="edit-button" id="edit-payment" style="display: none;">Edit</button>
                </div>
                <div class="section-content">
                    <div id="payment-component"></div>
                    <div id="watermark-container"></div>
                    <button type="button" id="place-order" class="btn btn-success btn-lg" style="display: none;">
                        <i class="fas fa-lock me-2"></i>
                        Place Order - $${this.orderData.amount?.toFixed(2) || '0.00'}
                    </button>
                </div>
                <div class="summary" id="payment-summary" style="display: none;"></div>
            </section>
        `;

        // Setup event listeners
        this.setupFormEventListeners(form);

        return form;
    }

    /**
     * Setup event listeners for the checkout form
     */
    setupFormEventListeners(form) {
        // Customer section
        const customerEmail = form.querySelector('#customer-email');
        const continueCustomer = form.querySelector('#continue-customer');
        const editCustomer = form.querySelector('#edit-customer');

        continueCustomer.addEventListener('click', () => this.handleCustomerContinue());
        editCustomer.addEventListener('click', () => this.editSection('customer'));

        // Shipping section
        const continueShipping = form.querySelector('#continue-shipping');
        const editShipping = form.querySelector('#edit-shipping');

        continueShipping.addEventListener('click', () => this.handleShippingContinue());
        editShipping.addEventListener('click', () => this.editSection('shipping'));

        // Payment section
        const placeOrder = form.querySelector('#place-order');
        const editPayment = form.querySelector('#edit-payment');

        placeOrder.addEventListener('click', () => this.handlePlaceOrder());
        editPayment.addEventListener('click', () => this.editSection('payment'));

        // Email validation
        customerEmail.addEventListener('blur', () => this.validateEmail());
    }

    /**
     * Handle customer information step
     */
    async handleCustomerContinue() {
        try {
            const email = document.getElementById('customer-email').value.trim();
            
            if (!this.validateEmailFormat(email)) {
                // this.showError('Please enter a valid email address');
                return;
            }

            this.showLoading('Checking customer information...');

            // Lookup customer with Fastlane
            const customerResponse = await this.fastlaneInstance.identity.lookupCustomerByEmail(email);
            
            if (customerResponse.customerContextId) {
                // Returning customer
                this.customerContextId = customerResponse.customerContextId;
                this.isGuestCustomer = false;
                
                // Trigger authentication
                const authResponse = await this.fastlaneInstance.identity.triggerAuthenticationFlow(
                    this.customerContextId
                );
                
                if (authResponse.authenticationState === 'succeeded') {
                    // Use stored addresses and payment methods
                    await this.handleReturningCustomer(authResponse.profileData);
                }
            } else {
                // New customer
                this.isGuestCustomer = true;
                await this.handleNewCustomer(email);
            }

            this.hideLoading();
            
        } catch (error) {
            console.error('Customer lookup error:', error);
            this.hideLoading();
            // this.showError(`Customer lookup failed: ${error.message}`);
        }
    }

    /**
     * Handle returning customer flow
     */
    async handleReturningCustomer(profileData) {
        console.log('Returning customer:', profileData);
        
        // Update customer summary
        this.updateSectionSummary('customer', `Email: ${profileData.email || 'Authenticated'}`);
        this.completeSection('customer');
        
        // Pre-populate shipping if available
        if (profileData.shippingAddress) {
            this.shippingAddress = profileData.shippingAddress;
            this.updateSectionSummary('shipping', this.formatAddressSummary(profileData.shippingAddress));
            this.completeSection('shipping');
            
            // Move directly to payment
            await this.initializePaymentComponent();
        } else {
            // Show shipping section
            this.activateSection('shipping');
            await this.initializeShippingComponent();
        }
    }

    /**
     * Handle new customer flow
     */
    async handleNewCustomer(email) {
        console.log('New customer:', email);
        
        // Update customer summary
        this.updateSectionSummary('customer', `Email: ${email}`);
        this.completeSection('customer');
        
        // Show shipping section
        this.activateSection('shipping');
        await this.initializeShippingComponent();
    }

    /**
     * Initialize shipping address component
     */
    async initializeShippingComponent() {
        try {
            const shippingContainer = document.getElementById('shipping-component');
            
            const shippingComponent = await this.fastlaneInstance.FastlaneShippingAddressComponent({
                onChange: (shippingAddress) => {
                    console.log('Shipping address changed:', shippingAddress);
                    this.shippingAddress = shippingAddress;
                    this.toggleContinueButton('shipping', !!shippingAddress);
                }
            });

            shippingComponent.render(shippingContainer);
            
        } catch (error) {
            console.error('Error initializing shipping component:', error);
            // this.showError('Failed to load shipping form');
        }
    }

    /**
     * Handle shipping continue
     */
    async handleShippingContinue() {
        if (!this.shippingAddress) {
            // this.showError('Please select a shipping address');
            return;
        }

        try {
            // Update shipping summary
            this.updateSectionSummary('shipping', this.formatAddressSummary(this.shippingAddress));
            this.completeSection('shipping');
            
            // Initialize payment component
            await this.initializePaymentComponent();
            
        } catch (error) {
            console.error('Shipping continue error:', error);
            // this.showError(`Shipping error: ${error.message}`);
        }
    }

    /**
     * Initialize payment component
     */
    async initializePaymentComponent() {
        try {
            this.activateSection('payment');
            
            const paymentContainer = document.getElementById('payment-component');
            const watermarkContainer = document.getElementById('watermark-container');
            
            const paymentComponent = await this.fastlaneInstance.FastlanePaymentComponent({
                onChange: async (paymentToken) => {
                    console.log('Payment token received:', paymentToken);
                    this.paymentToken = paymentToken;
                    this.toggleContinueButton('payment', !!paymentToken);
                }
            });

            // Render payment component
            await paymentComponent.render(paymentContainer);
            
            // Render watermark
            const watermarkComponent = await this.fastlaneInstance.FastlaneWatermarkComponent();
            await watermarkComponent.render(watermarkContainer);
            
        } catch (error) {
            console.error('Error initializing payment component:', error);
            // this.showError('Failed to load payment form');
        }
    }

    /**
     * Handle place order
     */
    async handlePlaceOrder() {
        if (!this.paymentToken) {
            this.showError('Please select a payment method');
            return;
        }

        try {
            this.showLoading('Processing your payment...');
            
            // Create payment on backend
            const paymentData = {
                order_id: this.orderData.id,
                paymentToken: this.paymentToken,
                shippingAddress: this.shippingAddress
            };

            const response = await fetch('/payment/create-fastlane', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCSRFToken()
                },
                credentials: 'same-origin',
                body: JSON.stringify(paymentData)
            });

            const result = await response.json();

            if (result.success) {
                this.hideLoading();
                this.showSuccess('Payment processed successfully! Redirecting...');
                
                // Redirect to success page
                setTimeout(() => {
                    window.location.href = `/payment/success/${result.payment_id}`;
                }, 2000);
                
            } else {
                throw new Error(result.error || 'Payment processing failed');
            }
            
        } catch (error) {
            console.error('Payment processing error:', error);
            this.hideLoading();
            //this.showError(`Payment failed: ${error.message}`);
        }
    }

    /**
     * Section management methods
     */
    activateSection(sectionName) {
        // Remove active class from all sections
        document.querySelectorAll('#checkout-form section').forEach(section => {
            section.classList.remove('active');
        });
        
        // Add active class to target section
        const targetSection = document.getElementById(`${sectionName}-section${sectionName === 'payment' ? '-form' : ''}`);
        if (targetSection) {
            targetSection.classList.add('active');
        }
    }

    completeSection(sectionName) {
        const section = document.getElementById(`${sectionName}-section${sectionName === 'payment' ? '-form' : ''}`);
        if (section) {
            section.classList.remove('active');
            section.classList.add('visited');
            
            // Show edit button
            const editButton = section.querySelector('.edit-button');
            if (editButton) {
                editButton.style.display = 'inline-block';
            }
        }
    }

    editSection(sectionName) {
        const section = document.getElementById(`${sectionName}-section${sectionName === 'payment' ? '-form' : ''}`);
        if (section) {
            section.classList.remove('visited');
            section.classList.add('active');
            
            // Hide edit button
            const editButton = section.querySelector('.edit-button');
            if (editButton) {
                editButton.style.display = 'none';
            }
        }
    }

    updateSectionSummary(sectionName, summaryText) {
        const summaryElement = document.getElementById(`${sectionName}-summary`);
        if (summaryElement) {
            summaryElement.textContent = summaryText;
            summaryElement.style.display = 'block';
        }
    }

    toggleContinueButton(sectionName, show) {
        const buttonId = sectionName === 'payment' ? 'place-order' : `continue-${sectionName}`;
        const button = document.getElementById(buttonId);
        if (button) {
            button.style.display = show ? 'block' : 'none';
        }
    }

    /**
     * Utility methods
     */
    validateEmailFormat(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    validateEmail() {
        const emailInput = document.getElementById('customer-email');
        const email = emailInput.value.trim();
        
        if (email && !this.validateEmailFormat(email)) {
            emailInput.classList.add('input-invalid');
            return false;
        } else {
            emailInput.classList.remove('input-invalid');
            return true;
        }
    }

    formatAddressSummary(address) {
        if (!address) return 'No address selected';
        
        const parts = [
            address.name?.fullName,
            address.address?.addressLine1,
            address.address?.addressLine2,
            `${address.address?.adminArea2}, ${address.address?.adminArea1} ${address.address?.postalCode}`,
            address.address?.countryCode
        ].filter(Boolean);
        
        return parts.join('\n');
    }

    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    /**
     * UI feedback methods
     */
    showLoading(message = 'Processing...') {
        if (this.loadingOverlay) {
            const messageElement = this.loadingOverlay.querySelector('p');
            if (messageElement) {
                messageElement.textContent = message;
            }
            this.loadingOverlay.style.display = 'flex';
        }
        
        // Disable payment section
        if (this.paymentSection) {
            this.paymentSection.classList.add('disabled');
        }
    }

    hideLoading() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'none';
        }
        
        // Re-enable payment section
        if (this.paymentSection) {
            this.paymentSection.classList.remove('disabled');
        }
    }

    showError(message) {
        if (this.errorMessage) {
            this.errorMessage.textContent = message;
            this.errorMessage.style.display = 'block';
        }
        
        if (this.successMessage) {
            this.successMessage.style.display = 'none';
        }
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            if (this.errorMessage) {
                this.errorMessage.style.display = 'none';
            }
        }, 10000);
    }

    showSuccess(message) {
        if (this.successMessage) {
            this.successMessage.textContent = message;
            this.successMessage.style.display = 'block';
        }
        
        if (this.errorMessage) {
            this.errorMessage.style.display = 'none';
        }
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (this.successMessage) {
                this.successMessage.style.display = 'none';
            }
        }, 5000);
    }

    /**
     * Fallback to standard PayPal buttons if Fastlane fails
     */
    initializeFallbackPayPal() {
        console.log('Initializing fallback PayPal buttons');
        
        if (!window.paypal) {
            this.showError('PayPal SDK not loaded. Please refresh the page.');
            return;
        }

        // Clear the container
        if (this.paypalButtonContainer) {
            this.paypalButtonContainer.innerHTML = '<h4>Standard PayPal Checkout</h4>';
        }

        // Render standard PayPal buttons
        window.paypal.Buttons({
            createOrder: async () => {
                try {
                    const response = await fetch('/payment/create', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': this.getCSRFToken()
                        },
                        credentials: 'same-origin',
                        body: JSON.stringify({
                            order_id: this.orderData.id,
                            payment_method: 'paypal'
                        })
                    });

                    const result = await response.json();
                    
                    if (result.success && result.approval_url) {
                        // For standard PayPal, we need to redirect to approval URL
                        window.location.href = result.approval_url;
                        return;
                    } else {
                        throw new Error(result.error || 'Failed to create PayPal payment');
                    }
                    
                } catch (error) {
                    console.error('PayPal button error:', error);
                    // this.showError(`PayPal error: ${error.message}`);
                }
            },
            
            onError: (error) => {
                console.error('PayPal button error:', error);
                this.showError('PayPal checkout failed. Please try again.');
            }
        }).render(this.paypalButtonContainer);
    }
}

// Initialize Fastlane checkout when script loads
const fastlaneCheckout = new FastlaneCheckout();

// Export for global access if needed
window.FastlaneCheckout = FastlaneCheckout;
